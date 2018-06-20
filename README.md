# Test Couchbase Operator

[![Build Status](https://travis-ci.org/spjmurray/tco.png?branch=master)](https://travis-ci.org/spjmurray/tco)

Simple wrapper around the E2E test framework which makes things easy for developers.

## Install

Simply copy ```tco``` into somewhere in your path.

## Configure

Most things are configurable on the CLI, however for optional parameters you can simply add them to ~/.tco/config and they will override the CLI parameters.  This is recommended for things that are static such as your ```repo``` or other things what are specific to a particular developer's Kubernetes set up.  The configuration is in YAML:

    ---
    repo: ~/go/src/github.com/couchbase/couchbase-operator

## Run

Simply specify a suite or individual test to run:

    $ tco --suite sanity
    $ tco --test TestRecoveryAfterOnePodFailureNoBucket

## Issues

Running an individual test is not yet possible.
