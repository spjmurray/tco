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
    'upgrade': 'TestUpgrade',
}

# Default arguements
DEFAULTS = {
    'namespace': 'default',
    'kubeconfig': '~/.kube/config',
    'service-account': 'default',
    'operator-image': 'couchbase/couchbase-operator:v1',
    'admission-image': 'couchbase/couchbase-operator-admission:v1',
    'storage-class': 'standard',
    'server-image': 'couchbase/server:enterprise-6.0.3',
    'server-upgrade-image': 'couchbase/server:enterprise-6.5.0-beta2',
}

# Hard coded paths relative to the repo
DEPLOYMENT_PATH_REL = '/example/deployment.yaml'
CLUSTERS_PATH_REL = '/test/e2e/resources/cluster_conf.yaml'
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

    def _gen_kube_config(self):
        """
        Create clusters that can be used (without modification) by the framework.
        By default use whatever is in the kube config.  If contexts are specified
        use them in the cluster configuration.  If too few are specified the last
        defined is replicated.
        """

        template = [
            {
                'name': 'BasicCluster',
                'config': self.args.kubeconfig,
            },
            {
                'name': 'NewCluster1',
                'config': self.args.kubeconfig,
            },
        ]

        if self.args.context:
            diff = len(template) - len(self.args.context)
            if diff >= 1:
                self.args.context += self.args.context[-1:] * diff
            for index, config in enumerate(template, 0):
                config['context'] = self.args.context[index]

        return template

    def _gen_test_config(self, suite):
        """
        Using CLI and static parameters create a test config file.
        This is only useful for test suites.
        """
        config = {
            'operator-image': self.args.image,
            'admission-controller-image': self.args.admission_controller_image,
            'namespace': self.args.namespace,
            'deployment-spec': self.args.repo + DEPLOYMENT_PATH_REL,
            # This should be dynamically generated can use AWS or something
            'cluster-config': self.args.repo + CLUSTERS_PATH_REL,
            # The tests use either of these clusters as they are set up differently
            'kube-config': self._gen_kube_config(),
            'duration': 7,
            'skip-tear-down': False,
            'suite': suite,
            'kube-type': 'kubernetes',
            'kube-version': '1.10.0-0',
            'serviceAccountName': self.args.service_account,
            'couchbase-server-image': self.args.server_image,
            'couchbase-server-image-upgrade': self.args.server_upgrade_image,
            'StorageClassName': self.args.storage_class,
            'collectLogsOnFailure': self.args.collect_logs,
        }

        if self.args.docker_server:
            config['docker-server'] = self.args.docker_server
            config['docker-username'] = self.args.docker_username
            config['docker-password'] = self.args.docker_password

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
                        'NewCluster1',
                    ],
                    'testcases': [{'name': test} for test in self.args.test],
                },
            ],
        }

        # Should be configurable rather than hard coded
        temp = tempfile.NamedTemporaryFile(suffix='.yaml', dir=self.args.repo + SUITES_PATH_REL)
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
            '-timeout', '16h',
            '-testconfig', test_config.name,
        ]
        self._exec(cmd)


def main():
    """
    Parse command line arguments and run the relevant test type
    """
    parser = argparse.ArgumentParser()

    # Generic arguments
    parser.add_argument('-n', '--namespace', default=DEFAULTS['namespace'])
    parser.add_argument('-k', '--kubeconfig', default=DEFAULTS['kubeconfig'])
    parser.add_argument('-c', '--context', action='append')
    parser.add_argument('-a', '--service-account', default=DEFAULTS['service-account'])
    parser.add_argument('-i', '--image', default=DEFAULTS['operator-image'])
    parser.add_argument('-I', '--admission-controller-image', default=DEFAULTS['admission-image'])
    parser.add_argument('-r', '--repo')
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-S', '--docker-server')
    parser.add_argument('-U', '--docker-username')
    parser.add_argument('-P', '--docker-password')
    parser.add_argument('-C', '--storage-class', default=DEFAULTS['storage-class'])
    parser.add_argument('-l', '--collect-logs', action='store_true')
    parser.add_argument('--server-image', default=DEFAULTS['server-image'])
    parser.add_argument('--server-upgrade-image', default=DEFAULTS['server-upgrade-image'])

    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--suite', choices=SUITES.keys())
    group.add_argument('-t', '--test', action='append')

    args = parser.parse_args()

    # Intialize logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(stream=sys.stdout, level=log_level)

    # Load up static arguments from the file system and add to the cli ones
    try:
        with open(os.environ['HOME'] + '/.tco/config') as config_file:
            static_config = yaml.load(config_file.read(), Loader=yaml.SafeLoader)
    except IOError:
        pass
    else:
        for key, value in static_config.items():
            setattr(args, key, value)

    # Check that required arguments are set
    required_args = [
        'namespace',
        'kubeconfig',
        'service_account',
        'image',
        'repo',
    ]
    for required_arg in required_args:
        if getattr(args, required_arg) == '':
            logging.error('Required argument %s unset', required_arg)

    # Check docker parameters are correctly set
    if args.docker_server:
        if not args.docker_username:
            logging.error('Required arguments --docker-username unset')
        if not args.docker_password:
            logging.error('Required arguments --docker-password unset')

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
