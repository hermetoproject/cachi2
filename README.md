# Cachi2

[![coverage][cachi2-coveralls-badge]][cachi2-coveralls]
[![container][cachi2-container-status]][cachi2-container]

Cachi2 is a CLI tool that pre-fetches your project's dependencies to aid in making your build process
[hermetic](https://slsa.dev/spec/v0.1/requirements#hermetic).

To see if we support your package manager(s), please check the [package managers](#package-managers) section.

The primary intended use of Cachi2's outputs is for network-isolated container builds (see [usage](docs/usage.md)).

## Table of contents

* [Goals](#goals)
* [Installation](#installation)
* [Basic usage](#basic-usage)
* [Configuration](#configuration)
* [Development](#development)
* [Releasing](#releasing)
* [Package managers](#package-managers)
* [Project status](#project-status)

## Goals

Please note that Cachi2 is rather picky, aiming to:

* encourage or enforce best practices
* never execute arbitrary code - looking at you [setup.py (discouraged)][setuppy-discouraged]
* keep the implementation simple

To play nicely with Cachi2, the build process for your project must be

* **Defined** - Cachi2 only fetches dependencies that are explicitly declared - typically in a lockfile generated by
  your package manager.
* **Reproducible** - Cachi2 will refuse to fetch a dependency if it's not pinned to an exact version. This goes
  for transitive dependencies as well (and ties to the Defined point). Most package managers pin all dependencies
  automatically in lockfiles.
* **Secure** - Even with a lockfile, your build is not truly safe from supply chain attacks (such as
  [dependency confusion](docs/dependency_confusion.md)) unless you verify the checksums of all dependencies. If your
  package manager supports specifying the expected checksums, we strongly encourage you to make use of them.

  ⚠ Cachi2 will verify checksums if present, but doesn't require them by default. This may change in the future.

In return, Cachi2 will help make your build

* **Auditable** - by generating a manifest of all the dependencies that go into your build.

The ability to achieve the goals depends on the hermeticity of the build process. Ideally, you should try to isolate the
build from both the internet and the underlying host system to avoid implicit dependencies, irreproducible behavior and
whole hosts of other issues. Cachi2 itself is not a hermetic build system. We suggest you take advantage of existing
technologies - such as containers - to achieve isolation (see [usage](docs/usage.md)).

## Installation

### Standalone

We do not distribute Cachi2 as a standalone package as of now.

To install Cachi2 for local development, see the [development](#development) section.

### Container image

[![container][cachi2-container-status]][cachi2-container]

```text
quay.io/redhat-appstudio/cachi2:latest
```

The container is re-built automatically on every merge to the main branch.

You may wish to set up an alias to make local usage more convenient:

```shell
alias cachi2='podman run --rm -ti -v "$PWD:$PWD:z" -w "$PWD" quay.io/redhat-appstudio/cachi2:latest'
```

Note that the alias mounts the current working directory - the container will have access to files in that directory
and nowhere else.

## Basic usage

```shell
cachi2 fetch-deps \
  --source ./my-repo \
  --output ./cachi2-output \
  gomod
```

The `fetch-deps` command fetches your project's dependencies and stores them on your disk. You can then use these
outputs to, say, build a container image.

See [docs/usage.md](docs/usage.md) for a more detailed, practical (*cough*) example of Cachi2 usage.

You might also like to check out `cachi2 --help` and the `--help` texts of the available subcommands.

## Configuration

You can change Cachi2's configuration by specifying a configuration file while invoking any of the CLI commands:

```shell
 cachi2 --config-file config.yaml fetch-deps --source ./my-repo gomod
```

Any parameter specified in this file will override the default values present in the
[config.py](cachi2/core/config.py) module.

The only supported format for the config file is YAML.

### Available configuration parameters

* `default_environment_variables` - a dictionary where the keys
are names of package managers. The values are dictionaries where the keys
are default environment variables to set for that package manager and the
values are the environment variable values.
* `gomod_download_max_tries` - a maximum number of attempts for retrying go commands.
* `gomod_strict_vendor` - the bool to disable/enable the strict vendor mode. For a repo that has gomod dependencies,
if the `vendor` directory exists and this config option is set to `True`, one of the
[vendoring flags](gomod.md#vendoring) must be used.
* `goproxy_url` - sets the value of the GOPROXY variable that Cachi2 uses internally
when downloading Go modules. See [Go environment variables](https://go.dev/ref/mod#environment-variables).
* `requests_timeout` - a number (in seconds) for `requests.get()`'s 'timeout' parameter,
  which sets an upper limit on how long `requests` can take to make a connection and/or send a response.
  Larger numbers set longer timeouts.
* `subprocess_timeout` - a number (in seconds) to set a timeout for commands executed by
  the `subprocess` module. Set a larger number to give the subprocess execution more time.

## Development

### Virtual environment

Set up a virtual environment that has everything you will need for development:

```shell
make venv
source venv/bin/activate
```

This installs the Cachi2 CLI in [editable mode](https://setuptools.pypa.io/en/latest/userguide/development_mode.html),
which means changes to the source code will reflect in the behavior of the CLI without the need for reinstalling.

You may need to install Python 3.9 in case you want to test your changes against Python 3.9 locally
before submitting a pull request.

```shell
dnf install python3.9
```

The CLI also depends on the following non-Python dependencies:

```shell
dnf install golang-bin git
```

You should now have everything needed to [try out](#basic-usage) the CLI or hack on the code in ~~vim~~ your favorite
editor.

### Developer flags

* `--dev-package-managers` (hidden): enables in-development package manager(s)
  for test. Please refer to other existing package managers to see how they're
  enabled and wired to the CLI.

  Invoke it as `cachi2 fetch-deps --dev-package-managers FOO`

  More explicitly

  * `--dev-package-managers` is a *flag for* `fetch-deps`
  * `FOO` is an *argument to* `fetch-deps` (i.e. the language to fetch for)

### Coding standards

Cachi2's codebase conforms to standards enforced by a collection of formatters, linters and other code checkers:

* [black](https://black.readthedocs.io/en/stable/) (with a line-length of 100) for consistent formatting
* [isort](https://pycqa.github.io/isort/) to keep imports sorted
* [flake8](https://flake8.pycqa.org/en/latest/) to (de-)lint the code and ~~politely~~ ask for docstrings
* [mypy](https://mypy.readthedocs.io/en/stable/) for type-checking. Please include type annotations for new code.
* [pytest](https://docs.pytest.org/en/7.1.x/) to run unit tests and report coverage stats. Please aim for (near) full
  coverage of new code.

Options for all the tools are configured in [pyproject.toml](./pyproject.toml) and [tox.ini](./tox.ini).

Run all the checks that your pull request will be subjected to:

```shell
make test
```

### Error message guidelines

We try to keep error messages friendly and actionable.

* If there is a known solution, the error message should politely suggest the solution.
  * Include a link to the documentation when suitable.
* If there is no known solution, suggest where to look for help.
* If retrying is a possible solution, suggest retrying and where to look for help if the issue persists.

The error classes aim to encourage these guidelines. See the [errors.py](cachi2/core/errors.py) module.

### Running unit tests

Run all unit tests (but no other checks):

```shell
make test-unit
```

For finer control over which tests get executed, e.g. to run all tests in a specific file, activate
the [virtualenv](#virtual-environment) and run:

```shell
tox -e py39 -- tests/unit/test_cli.py
```

Even better, run it stepwise (exit on first failure, re-start from the failed test next time):

```shell
tox -e py39 -- tests/unit/test_cli.py --stepwise
```

You can also run a single test class or a single test method:

```shell
tox -e py39 -- tests/unit/test_cli.py::TestGenerateEnv
tox -e py39 -- tests/unit/test_cli.py::TestGenerateEnv::test_invalid_format
tox -e py39 -- tests/unit/extras/test_envfile.py::test_cannot_determine_format
```

In short, tox passes all arguments to the right of `--` directly to pytest.

### Running integration tests

Build Cachi2 image (localhost/cachi2:latest) and run most integration tests:

```shell
make test-integration
```

Run tests which requires a local PyPI server as well:

```shell
make test-integration TEST_LOCAL_PYPISERVER=true
```

Note: while developing, you can run the PyPI server with `tests/pypiserver/start.sh &`.

To run integration-tests with custom image, specify the CACHI2\_IMAGE environment variable. Examples:

```shell
CACHI2_IMAGE=quay.io/redhat-appstudio/cachi2:{tag} tox -e integration
CACHI2_IMAGE=localhost/cachi2:latest tox -e integration
```

Similarly to unit tests, for finer control over which tests get executed, e.g. to run only 1 specific test case, execute:

```shell
tox -e integration -- tests/integration/test_package_managers.py::test_packages[gomod_without_deps]
```

### Running integration tests and generating new test data

To re-generate new data (output, dependencies checksums, vendor checksums) and run integration tests with them:

```shell
make GENERATE_TEST_DATA=true test-integration
```

Generate data for test cases matching a pytest pattern:

```shell
CACHI2_GENERATE_TEST_DATA=true tox -e integration -- -k gomod
```

### Adding new dependencies to the project

Sometimes when working on adding a new feature you may need to add a new dependency to the project.
Usually, one commonly goes about it by adding the dependency to one of the ``requirements`` files
or the more modern and standardized ``pyproject.toml`` file.
In our case, dependencies must always be added to the ``pyproject.toml`` file as the
``requirements`` files are generated by the ``pip-compile`` tool to not only pin versions of all
dependencies but also to resolve and pin transitive dependencies. Since our ``pip-compile``
environment is tied to Python 3.9, we have a Makefile target that runs the tool in a container
image so you don't have to install another Python version locally just because of this. To
re-generate the set of dependencies, run the following in the repository and commit the changes:

```
$ make pip-compile
```

## Releasing

To release a new version of Cachi2, simply create a [GitHub release][cachi2-releases]. Note that
Cachi2 follows [semantic versioning](https://semver.org/) rules.

Upon release, the [.tekton/release.yaml](.tekton/release.yaml) pipeline tags the corresponding
[Cachi2 image][cachi2-container] with the newly released version tag (after validating that the
tag follows the expected format: `$major.$minor.$patch`, without a `v` prefix).

*You apply a release tag to a specific commit. The [.tekton/push.yaml](.tekton/push.yaml) pipeline
should have built the image for that commit already. This is the "corresponding image" that receives
the new version tag. If the image for the tagged commit does not exist, the release pipeline will fail.*

You can watch the release pipeline in the [OpenShift console][ocp-cachi2-pipelines] in case it fails
(the pipeline is not visible anywhere in GitHub UI). For intermittent failures, retrying should be
possible from the OpenShift UI or by deleting and re-pushing the version tag.

*⚠ The release pipeline runs as soon as you push a tag into the repository. Do not push the new version
tag until you are ready to publish the release. You can use GitHub's ability to auto-create the tag
upon publishment.*

## Package managers

Supported:

* [gomod](#gomod)
* [pip](#pip)
* [npm](#npm)
* [yarn](#yarn)

Planned:

* dnf
* cargo
* rubygems

*Based on the [supported package managers](https://github.com/containerbuildsystem/cachito#package-managers) in the
original Cachito.*

### gomod

<https://go.dev/ref/mod>

Current version: 1.21 [^go-version] [^go-compat]

The gomod package manager works by parsing the [go.mod](https://go.dev/ref/mod#go-mod-file) file present in the source
repository to determine which dependencies to download. Cachi2 does not parse this file on its own - rather, we rely on
the `go` command to download and list the required dependencies.

From go 1.17 onward, the go.mod file includes all the transitively required dependencies of your application - see the
section about *Pruned module graphs* in the [1.17 changelog][go117-changelog]. In previous go versions, the go.mod file
included only direct dependencies. Cachi2 does support downloading and listing all transitive dependencies for earlier
versions thanks to Go's backwards compatibility[^go-compat]. Note that using go >= 1.17 in your project has the added
benefit of downloading fewer dependencies (as noted in the changelog), in some cases drastically so.

See [docs/gomod.md](docs/gomod.md) for more details.

[^go-version]: Cachi2 expects to use a specific version of the `go` command when downloading dependencies. This is the
  version installed in the [cachi2 container](#container-image). We do not guarantee correctness if you run Cachi2
  locally (outside the container) with a different Go version. You *are* free to use a different version to build your
  project.

[^go-compat]: The `go` command promises to be backwards compatible with previous versions. If your go.mod file specifies
  the intended go version, Cachi2 should handle it appropriately. If your go version is *higher* than what Cachi2 uses,
  there is a good chance it will be compatible regardless, as long as the dependency resolution did not change between
  the two versions. For example, dependency resolution did change in [go 1.18][go118-changelog] but not in
  [go 1.19][go119-changelog]. Things are a bit more complicated with [Go 1.21][go121-changelog], if
  you are or have been experiencing issues with cachi2 related to Go 1.21+, please refer to
  [docs/gomod.md](docs/gomod.md#go-121-since-cachi2-v050).

### pip

<https://pip.pypa.io/en/stable/>

Cachi2 supports pip by parsing [requirements.txt](https://pip.pypa.io/en/stable/reference/requirements-file-format/)
files present in the source repository and downloading the declared dependencies.

The files must be lockfiles, i.e. declare all the transitive dependencies and pin them to specific versions. Generating
such a lockfile is best done using tools like [pip-compile](https://pip-tools.readthedocs.io/en/stable/).

We support source distribution file format ([sdist][sdist-spec]) as well as binary distribution file format ([wheel][wheel-spec]).

See [docs/pip.md](docs/pip.md) for more details.

### npm

<https://docs.npmjs.com/>

Cachi2 supports npm by parsing [package-lock.json](https://docs.npmjs.com/cli/v9/configuring-npm/package-lock-json)
file present in the source repository and downloading the declared dependencies.

To generate lockfile or to make sure the file is up to date,
you can use [npm install](https://docs.npmjs.com/cli/v9/commands/npm-install?v=true).

Make sure lockfile version is higher than v1 (Node.js 15 or higher).

See [docs/npm.md](docs/npm.md) for more details.

### yarn

<https://v3.yarnpkg.com/>

Current version: v3

Unlike NPM, cachi2 merely drives the underlying ``yarn`` CLI command operations, that is, cachi2
leaves most of the heavy lifting to Yarn itself and it mainly focuses on post-process validation.
Note that having a Yarn lockfile (``yarn.lock``) checked into the repository is paramount for
cachi2 to process a project successfully. If missing, you can easily generate one by running [yarn
install](https://v3.yarnpkg.com/getting-started/usage#installing-all-the-dependencies)
prior to pointing cachi2 to your project.

See [docs/yarn.md](docs/yarn.md) for more details.

## Project status

Cachi2 was derived (but is not a direct fork) from [Cachito](https://github.com/containerbuildsystem/cachito) and is
still in early development phase.

[cachi2-coveralls]: https://coveralls.io/github/containerbuildsystem/cachi2?branch=main
[cachi2-coveralls-badge]: https://coveralls.io/repos/github/containerbuildsystem/cachi2/badge.svg?branch=main
[cachi2-container]: https://quay.io/repository/redhat-appstudio/cachi2
[cachi2-container-status]: https://quay.io/repository/redhat-appstudio/cachi2/status
[cachi2-releases]: https://github.com/containerbuildsystem/cachi2/releases
[sdist-spec]: https://packaging.python.org/en/latest/specifications/source-distribution-format/
[wheel-spec]: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
[setuppy-discouraged]: https://setuptools.pypa.io/en/latest/userguide/quickstart.html#setuppy-discouraged
[go117-changelog]: https://tip.golang.org/doc/go1.17#go-command
[go118-changelog]: https://tip.golang.org/doc/go1.18#go-command
[go119-changelog]: https://tip.golang.org/doc/go1.19#go-command
[go121-changelog]: https://tip.golang.org/doc/go1.21
[ocp-cachi2-pipelines]: https://console-openshift-console.apps.stone-prd-rh01.pg1f.p1.openshiftapps.com/pipelines/ns/tekton-ci/pipeline-runs?name=cachi2
