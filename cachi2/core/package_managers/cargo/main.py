import logging
import textwrap
from dataclasses import dataclass
from functools import cached_property
from itertools import chain
from typing import Optional

import tomlkit
from packageurl import PackageURL
from tomlkit.toml_file import TOMLFile

from cachi2.core.models.input import Request
from cachi2.core.models.output import Component, EnvironmentVariable, ProjectFile, RequestOutput
from cachi2.core.rooted_path import RootedPath
from cachi2.core.scm import get_repo_id
from cachi2.core.utils import first_for, run_cmd

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CargoPackage:
    """CargoPackage."""

    name: str
    version: str
    source: Optional[str] = None  # [git|registry]+https://github.com/<org>/<package>#[|<sha>]
    checksum: Optional[str] = None
    dependencies: Optional[list] = None
    vcs_url: Optional[str] = None

    @cached_property
    def purl(self) -> PackageURL:
        """Return corrsponding purl."""
        qualifiers = {}
        if self.source is not None:
            qualifiers.update({"source": self.source})
        if self.vcs_url is not None:
            qualifiers.update({"vcs_url": self.vcs_url})
        if self.checksum is not None:
            qualifiers.update({"checksum": self.checksum})
        return PackageURL(type="cargo", name=self.name, version=self.version, qualifiers=qualifiers)

    def to_component(self) -> Component:
        """Convert CargoPackage into SBOM component."""
        return Component(name=self.name, version=self.version, purl=self.purl.to_string())


def fetch_cargo_source(request: Request) -> RequestOutput:
    """Fetch the source code for all cargo packages specified in a request."""
    components: list[Component] = []
    environment_variables: list[EnvironmentVariable] = []
    project_files: list[ProjectFile] = []

    for package in request.cargo_packages:
        package_dir = request.source_dir.join_within_root(package.path)
        components.extend(_resolve_cargo_package(package_dir, request.output_dir))
        # cargo allows to specify configuration per-package
        # https://doc.rust-lang.org/cargo/reference/config.html#hierarchical-structure
        project_files.append(_use_vendored_sources(package_dir))

    return RequestOutput.from_obj_list(components, environment_variables, project_files)


def _resolve_cargo_package(package_dir: RootedPath, output_dir: RootedPath) -> chain[Component]:
    """Resolve a single cargo package."""
    vendor_dir = output_dir.join_within_root("deps/cargo")
    cmd = ["cargo", "vendor", "--locked", str(vendor_dir)]
    log.info("Fetching cargo dependencies at %s", package_dir)
    run_cmd(cmd=cmd, params={"cwd": package_dir})

    # 'value' unwraps the underlying dict and that makes mypy happy (it complains about
    # mismatching type otherwise despite parsed document having the necessary interface).
    packages = tomlkit.parse((package_dir.path / "Cargo.lock").read_text()).value["package"]
    is_a_dep = lambda p: p["name"] != package_dir.path.stem  # a shorthand, thus # noqa: E731
    deps_components = (CargoPackage(**p).to_component() for p in packages if is_a_dep(p))

    is_main = lambda p: not is_a_dep(p)  # noqa: E731
    vcs_url = get_repo_id(package_dir.root).as_vcs_url_qualifier()
    main_package = first_for(is_main, packages, None)
    main_component = CargoPackage(
        name=main_package["name"], version=main_package["version"], vcs_url=vcs_url
    ).to_component()

    components = chain((main_component,), deps_components)

    return components


def _use_vendored_sources(package_dir: RootedPath) -> ProjectFile:
    """Make sure cargo will use the vendored sources when building the project."""
    cargo_config = package_dir.join_within_root(".cargo/config.toml")
    cargo_config.path.parent.mkdir(parents=True, exist_ok=True)
    cargo_config.path.touch(exist_ok=True)

    template = """
    [source.crates-io]
    replace-with = "vendored-sources"

    [source.vendored-sources]
    directory = "${output_dir}/deps/cargo"
    """

    toml_file = TOMLFile(cargo_config)
    original_content = toml_file.read()
    original_content.update(tomlkit.parse(textwrap.dedent(template)))
    toml_file.write(original_content)

    return ProjectFile(abspath=cargo_config.path, template=template)
