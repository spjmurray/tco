#!/usr/bin/env python

"""
Runs Couchbase operator tests in an easy to use manner for developers
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import yaml


# Suite aliases
SUITES = {
    'sanity': 'TestSanity',
    'p0': 'TestP0',
    'p1': 'TestP1',
    'crd': 'TestCRDValidation',
}

# Hard coded paths relative to the repo
DEPLOYMENT_PATH_REL = '/example/deployment.yaml'
CLUSTERS_PATH_REL = '/test/e2e/resources/cluster_conf.yml'
SUITES_PATH_REL = '/test/e2e/resources/suites'

class TestRunner(object):
    """
    Runs tests based on the provided context
    """

    def __init__(self, args):
        self.args = args

    def _yaml_encode(self, data):
        """
        Encode a data structure into yaml and optionally prints
        """
        enc = yaml.dump(data, default_flow_style=False)
        logging.debug(enc)
        return enc

    def _gen_test_config(self, suite):
        """
        Using CLI and static parameters create a test config file.
        This is only useful for test suites.
        """
        config = {
            'operator-image': self.args.image,
            'namespace': self.args.namespace,
            'deployment-spec': self.args.repo + DEPLOYMENT_PATH_REL,
            # This should be dynamically generated can use AWS or something
            'cluster-config': self.args.repo + CLUSTERS_PATH_REL,
            'kube-config': [
                {
                    'name': 'BasicCluster',
                    'config': self.args.kubeconfig,
                },
            ],
            'duration': 7,
            'skip-tear-down': False,
            'suite': suite,
            'kube-type': 'kubernetes',
            'kube-version': '1.10.0-0',
            'serviceAccountName': self.args.service_account,
        }

        temp = tempfile.NamedTemporaryFile()
        temp.write(self._yaml_encode(config))
        temp.flush()
        return temp

    def _get_suite_config(self):
        """
        Generates a suite to test a specific test
        """
        config = {
            'suite': 'TestSingle',
            'timeout': '240m',
            'tcGroups': [
                {
                    'name': 'Group1',
                    'clusters': [
                        'BasicCluster',
                    ],
                    'testcases': [
                        {
                            'name': self.args.test,
                        },
                    ],
                },
            ],
        }

        # Should be configurable rather than hard coded
        temp = tempfile.NamedTemporaryFile(suffix='.yml', dir=self.args.repo + SUITES_PATH_REL)
        temp.write(self._yaml_encode(config))
        temp.flush()
        return temp

    def _exec(self, cmd):
        """
        Execute a command with necessary environment variables etc
        """
        # Required for the suite to find cbopctl
        os.environ['TESTDIR'] = os.path.expanduser(self.args.repo)
        proc = subprocess.Popen(cmd, env=os.environ)
        proc.communicate()

    def run(self):
        """
        Run the requested test(s)
        """

        # Select the suite from our list of aliases or if a specific
        # test is requested then create a temporary suite
        if self.args.suite:
            suite_name = SUITES[self.args.suite]
        else:
            suite_config = self._get_suite_config()
            filename = os.path.basename(suite_config.name)
            suite_name, _ = os.path.splitext(filename)

        # Generate the test configuration and run the test
        test_config = self._gen_test_config(suite_name)
        cmd = [
            'go', 'test', 'github.com/couchbase/couchbase-operator/test/e2e',
            '-run', 'TestOperator',
            '-v',
            '-race',
            '-timeout', '240m',
            '-testconfig', test_config.name,
        ]
        self._exec(cmd)


def main():
    """
    Parse command line arguments and run the relevant test type
    """
    parser = argparse.ArgumentParser()

    # Generic arguments
    parser.add_argument('-n', '--namespace', default='default')
    parser.add_argument('-k', '--kubeconfig', default='~/.kube/config')
    parser.add_argument('-a', '--service-account', default='default')
    parser.add_argument('-i', '--image', default='couchbase/couchbase-operator:v1')
    parser.add_argument('-r', '--repo')
    parser.add_argument('-v', '--verbose', action='store_true')

    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--suite', choices=SUITES.keys())
    group.add_argument('-t', '--test')

    args = parser.parse_args()

    # Intialize logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=log_level)

    # Load up static arguments from the file system and add to the cli ones
    try:
        with open(os.environ['HOME'] + '/.tco/config') as config_file:
            static_config = yaml.load(config_file.read())
    except IOError:
        pass
    else:
        for key, value in static_config.items():
            setattr(args, key, value)

    # Expand paths
    args_paths = [
        'kubeconfig',
        'repo',
    ]
    for args_path in args_paths:
        setattr(args, args_path, os.path.expanduser(getattr(args, args_path)))

    logging.debug(args)

    # Run the tests
    runner = TestRunner(args)
    return runner.run()


if __name__ == '__main__':
    main()
