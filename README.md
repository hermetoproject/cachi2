# Cachi2

[![coverage][cachi2-coverage-badge]][cachi2-coverage-status]
[![container][cachi2-container-badge]][cachi2-container-status]

Cachi2 is a CLI tool that pre-fetches your project's dependencies to aid in making your build process
[hermetic](https://slsa.dev/spec/v0.1/requirements#hermetic).

To see if we support your package manager(s), please check the [package managers](#package-managers) section.

The primary intended use of Cachi2's outputs is for network-isolated container builds (see [usage](docs/usage.md)).

## Table of contents

* [Goals](#goals)
* [Installation](#installation)
* [Basic usage](#basic-usage)
* [Configuration](#configuration)
* [Package managers](#package-managers)
* [Project status](#project-status)
* [Contributing](CONTRIBUTING.md)

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

To install Cachi2 for local development, see the [CONTRIBUTING.md](CONTRIBUTING.md).

### Container image

[![container][cachi2-container-badge]][cachi2-container-status]

```text
quay.io/konflux-ci/cachi2:latest
```

The container is re-built automatically on every merge to the main branch.

You may wish to set up an alias to make local usage more convenient:

```shell
alias cachi2='podman run --rm -ti -v "$PWD:$PWD:z" -w "$PWD" quay.io/konflux-ci/cachi2:latest'
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
* `gomod_strict_vendor` - (deprecated) the bool to disable/enable the strict vendor mode. For a repo that has gomod
dependencies, if the `vendor` directory exists and this config option is set to `True`, one of the vendoring flags
must be used.
  *This option no longer has any effect when set. Check the  [vendoring docs](docs/gomod.md#vendoring) for
  more information.*
* `goproxy_url` - sets the value of the GOPROXY variable that Cachi2 uses internally
when downloading Go modules. See [Go environment variables](https://go.dev/ref/mod#environment-variables).
* `requests_timeout` - a number (in seconds) for `requests.get()`'s 'timeout' parameter,
  which sets an upper limit on how long `requests` can take to make a connection and/or send a response.
  Larger numbers set longer timeouts.
* `subprocess_timeout` - a number (in seconds) to set a timeout for commands executed by
  the `subprocess` module. Set a larger number to give the subprocess execution more time.

## Package managers

Supported:

* [gomod](#gomod)
* [pip](#pip)
* [npm](#npm)
* [yarn](#yarn)
* [bundler](#bundler)
* [generic fetcher](#generic-fetcher)

Planned:

* dnf
* cargo

### gomod

<https://go.dev/ref/mod>

Current version: 1.24 [^go-version] [^go-compat]

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

<https://yarnpkg.com/>

Current version: v4

Unlike NPM, cachi2 merely drives the underlying ``yarn`` CLI command operations, that is, cachi2
leaves most of the heavy lifting to Yarn itself and it mainly focuses on post-process validation.
Note that having a Yarn lockfile (``yarn.lock``) checked into the repository is paramount for
cachi2 to process a project successfully. If missing, you can easily generate one by running [yarn
install](https://v3.yarnpkg.com/getting-started/usage#installing-all-the-dependencies)
prior to pointing cachi2 to your project.

See [docs/yarn.md](docs/yarn.md) for more details.

### bundler

<https://bundler.io/>

Cachi2 supports bundler by parsing the [Gemfile.lock](https://bundler.io/guides/using_bundler_in_applications.html#gemfilelock)
file present in the source repository and downloading the declared dependencies.

To generate a lockfile or to make sure the file is up to date, you can use
for example the `bundle lock` command, which generates the `Gemfile.lock` file based
on the dependencies specified in the [Gemfile](https://bundler.io/v2.5/man/gemfile.5.html).
Both files must be present in the source repository so you should check them into your git repository.

See [docs/bundler.md](docs/bundler.md) for more details.

### generic fetcher

Generic fetcher is a way for Cachi2 to support prefetching arbitrary files that don't fit into other package managers.
With the generic fetcher, you can easily fetch those files with Cachi2 along with your other language-specific dependencies,
satisfy the hermetic build condition and have them recorded in the SBOM.

Cachi2 uses a simple custom lockfile named `artifacts.lock.yaml` that is expected to be present in the repository, or
supplied in JSON input. The lockfile describes the urls, checksums and output filenames for the downloaded files.

Currently supported types of artifacts:
- Arbitrary files
- Maven artifacts

See [docs/generic.md](docs/generic.md) for more details.

## Project status

Cachi2 was derived (but is not a direct fork) from [Cachito](https://github.com/containerbuildsystem/cachito).

[cachi2-coverage-badge]: https://codecov.io/github/containerbuildsystem/cachi2/graph/badge.svg?token=VJKRTZQBMY
[cachi2-coverage-status]: https://codecov.io/github/containerbuildsystem/cachi2

[cachi2-container-badge]: https://img.shields.io/badge/container-latest-blue
[cachi2-container-status]: https://quay.io/repository/konflux-ci/cachi2/tag/latest

[sdist-spec]: https://packaging.python.org/en/latest/specifications/source-distribution-format/
[wheel-spec]: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
[setuppy-discouraged]: https://setuptools.pypa.io/en/latest/userguide/quickstart.html#setuppy-discouraged
[go117-changelog]: https://tip.golang.org/doc/go1.17#go-command
[go118-changelog]: https://tip.golang.org/doc/go1.18#go-command
[go119-changelog]: https://tip.golang.org/doc/go1.19#go-command
[go121-changelog]: https://tip.golang.org/doc/go1.21
