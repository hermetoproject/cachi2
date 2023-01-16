# SPDX-License-Identifier: GPL-3.0-or-later

import logging
import os
from pathlib import Path
from typing import List

import pytest

from . import utils

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/cachito-gomod-with-deps.git",
                ref="4c65d49cae6bfbada4d479b321d8c0109fa1aa97",
                packages=({"path": ".", "type": "gomod"},),
                check_vendor_checksums=False,
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            id="gomod_with_deps",
        ),
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/cachito-gomod-without-deps.git",
                ref="a888f7261b9a9683972fbd77da2d12fe86faef5e",
                packages=({"path": ".", "type": "gomod"},),
                check_vendor_checksums=False,
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            id="gomod_without_deps",
        ),
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendored.git",
                ref="ff1960095dd158d3d2a4f31d15b244c24930248b",
                packages=({"path": ".", "type": "gomod"},),
                check_output_json=False,
                check_deps_checksums=False,
                check_vendor_checksums=False,
                expected_exit_code=2,
                expected_output='The "gomod-vendor" or "gomod-vendor-check" flag'
                " must be set when your repository has vendored dependencies",
            ),
            id="gomod_vendored_without_flag",
        ),
        # Test case checks if vendor folder with dependencies will remain unchanged in cloned
        # source repo, deps folder in output folder should be empty.
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendored.git",
                ref="ff1960095dd158d3d2a4f31d15b244c24930248b",
                packages=({"path": ".", "type": "gomod"},),
                flags=["--gomod-vendor"],
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            id="gomod_vendored_with_flag",
        ),
        # Test case checks if vendor folder will be created with dependencies in cloned
        # source repo, deps folder in output folder should be empty.
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendor-check-no-vendor.git",
                ref="7ba383d5592910edbf7f287d4b5a00c5ababf751",
                packages=({"path": ".", "type": "gomod"},),
                flags=["--gomod-vendor-check"],
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            id="gomod_vendor_check_no_vendor",
        ),
        # Test case checks if vendor folder with dependencies will remain unchanged in cloned
        # source repo, deps folder in output folder should be empty.
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendor-check-pass.git",
                ref="0543a5034b687df174c6b12b7b6b9c04770a856f",
                packages=({"path": ".", "type": "gomod"},),
                flags=["--gomod-vendor-check"],
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            id="gomod_vendor_check_correct_vendor",
        ),
        # Test case checks if request will fail when source provided wrong vendor.
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendor-check-fail.git",
                ref="8553df6498705b2b36614320ca0c65bc24a1d9e6",
                packages=({"path": ".", "type": "gomod"},),
                flags=["--gomod-vendor-check"],
                check_output_json=False,
                check_deps_checksums=False,
                check_vendor_checksums=False,
                expected_exit_code=2,
                expected_output=(
                    "PackageRejected: The content of the vendor directory is not "
                    "consistent with go.mod. Please check the logs for more details"
                ),
            ),
            id="gomod_vendor_check_wrong_vendor",
        ),
        # Test case checks if request will fail when source provided empty vendor.
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/gomod-vendor-check-empty-vendor.git",
                ref="9989e210ac2993196e22d0a23fe18ce460012058",
                packages=({"path": ".", "type": "gomod"},),
                flags=["--gomod-vendor-check"],
                check_output_json=False,
                check_deps_checksums=False,
                check_vendor_checksums=False,
                expected_exit_code=2,
                expected_output=(
                    "PackageRejected: The content of the vendor directory is not "
                    "consistent with go.mod. Please check the logs for more details"
                ),
            ),
            id="gomod_vendor_check_empty_vendor",
        ),
    ],
)
def test_packages(
    test_params: utils.TestParameters,
    cachi2_image: utils.ContainerImage,
    tmpdir: Path,
    test_data_dir: Path,
    request: pytest.FixtureRequest,
):
    """
    Test fetched dependencies for package managers.

    :param test_params: Test case arguments
    :param tmpdir: Temp directory for pytest
    """
    test_case = request.node.callspec.id

    source_folder = utils.clone_repository(
        test_params.repo, test_params.ref, f"{test_case}-source", tmpdir
    )

    _ = utils.fetch_deps_and_check_output(
        tmpdir, test_case, test_params, source_folder, test_data_dir, cachi2_image
    )


@pytest.mark.parametrize(
    "test_params,check_cmd",
    [
        # Test case checks fetching retrodep dependencies, generating environment vars file,
        # building image with all prepared prerequisites and printing help message for retrodep
        # app in built image
        pytest.param(
            utils.TestParameters(
                repo="https://github.com/cachito-testing/retrodep.git",
                ref="c3496edd5d45523a1ed300de1575a212b86d00d3",
                packages=({"path": ".", "type": "gomod"},),
                check_vendor_checksums=False,
                expected_exit_code=0,
                expected_output="All dependencies fetched successfully",
            ),
            ["retrodep", "--help"],
            id="gomod_e2e_test",
        ),
    ],
)
def test_e2e(
    test_params: utils.TestParameters,
    check_cmd: List[str],
    cachi2_image: utils.ContainerImage,
    tmpdir: Path,
    test_data_dir: Path,
    request: pytest.FixtureRequest,
):
    """
    End to end test for package managers.

    :param test_params: Test case arguments
    :param tmpdir: Temp directory for pytest
    """
    test_case = request.node.callspec.id

    source_folder = utils.clone_repository(
        test_params.repo, test_params.ref, f"{test_case}-source", tmpdir
    )

    output_folder = utils.fetch_deps_and_check_output(
        tmpdir, test_case, test_params, source_folder, test_data_dir, cachi2_image
    )

    log.info("Create cachi2.env file")
    env_vars_file = os.path.join(tmpdir, "cachi2.env")
    cmd = [
        "generate-env",
        output_folder,
        "--output",
        env_vars_file,
        "--for-output-dir",
        os.path.join("/tmp", f"{test_case}-output"),
    ]
    (output, exit_code) = cachi2_image.run_cmd_on_image(cmd, tmpdir)
    assert exit_code == 0, f"Env var file creation failed. output-cmd: {output}"

    log.info("Build container image with all prerequisites retrieved in previous steps")
    container_folder = os.path.join(test_data_dir, test_case, "container")

    with utils.build_image(
        tmpdir, os.path.join(container_folder, "Containerfile"), test_case
    ) as test_image:
        log.info(f"Run command {check_cmd} on built image {test_image.repository}")
        (output, exit_code) = test_image.run_cmd_on_image(check_cmd, tmpdir)
        assert exit_code == 0, f"{check_cmd} command failed, Output: {output}"
