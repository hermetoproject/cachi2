# SPDX-License-Identifier: GPL-3.0-or-later
from datetime import datetime
from unittest import mock

import git
import pytest

from cachito.workers import scm
from cachito.errors import CachitoError

url = 'https://github.com/release-engineering/retrodep.git'
ref = 'c50b93a32df1c9d700e3e80996845bc2e13be848'
archive_path = f'/tmp/cachito-archives/release-engineering/retrodep/{ref}.tar.gz'


def test_repo_name():
    git_obj = scm.Git(url, ref)
    assert git_obj.repo_name == 'release-engineering/retrodep'


@mock.patch('tarfile.open')
@mock.patch('tempfile.TemporaryDirectory')
@mock.patch('git.repo.Repo.clone_from')
def test_clone_and_archive(mock_clone, mock_temp_dir, mock_tarfile_open):
    # Mock the archive being created
    mock_tarfile = mock.Mock()
    mock_tarfile_open.return_value.__enter__.return_value = mock_tarfile
    # Mock the commit being returned from repo.commit(self.ref)
    mock_commit = mock.Mock()
    mock_clone.return_value.commit.return_value = mock_commit
    # Mock the tempfile.TemporaryDirectory context manager
    mock_temp_dir.return_value.__enter__.return_value = '/tmp/cachito-temp'

    git_obj = scm.Git(url, ref)

    with mock.patch.object(git_obj.sources_dir, 'archive_path', new=archive_path):
        git_obj.clone_and_archive()

    # Verify the tempfile.TemporaryDirectory context manager was used
    mock_temp_dir.return_value.__enter__.assert_called_once()
    # Verify the repo was cloned and checked out properly
    mock_clone.assert_called_once_with(
        url, '/tmp/cachito-temp/repo',
        no_checkout=True, env={'GIT_TERMINAL_PROMPT': '0'}
    )
    assert mock_clone.return_value.head.reference == mock_commit
    mock_clone.return_value.head.reset.assert_called_once_with(index=True, working_tree=True)
    # Verfiy the archive was created
    mock_tarfile.add.assert_called_once_with(mock_clone.return_value.working_dir, 'app')


@mock.patch('tempfile.TemporaryDirectory')
@mock.patch('git.repo.Repo.clone_from')
def test_clone_and_archive_clone_failed(mock_git_clone, mock_temp_dir):
    # Mock the tempfile.TemporaryDirectory context manager
    mock_temp_dir.return_value.__enter__.return_value = '/tmp/cachito-temp'
    # Mock the git clone call
    mock_git_clone.side_effect = git.GitCommandError('some error', 1)

    git_obj = scm.Git(url, ref)
    with pytest.raises(CachitoError, match='Cloning the Git repository failed'):
        git_obj.clone_and_archive()


@mock.patch('tempfile.TemporaryDirectory')
@mock.patch('git.repo.Repo.clone_from')
def test_clone_and_archive_checkout_failed(mock_git_clone, mock_temp_dir):
    # Mock the tempfile.TemporaryDirectory context manager
    mock_temp_dir.return_value.__enter__.return_value = '/tmp/cachito-temp'
    # Mock the git calls
    mock_git_clone.return_value.commit.side_effect = git.GitCommandError('commit is invalid', 1)

    git_obj = scm.Git(url, ref)
    expected = (
        'Checking out the Git repository failed. Please verify the supplied reference of '
        f'"{ref}" is valid.'
    )
    with mock.patch.object(git_obj.sources_dir, 'archive_path', new=archive_path):
        with pytest.raises(CachitoError, match=expected):
            git_obj.clone_and_archive()


@mock.patch('tarfile.is_tarfile', return_value=True)
def test_fetch_source_archive_exists(mock_is_tarfile):
    scm_git = scm.Git(url, ref)

    po = mock.patch.object
    with po(scm_git.sources_dir.archive_path, 'exists', return_value=True):
        with po(scm_git.sources_dir.package_dir, 'glob') as glob:
            scm_git.fetch_source()
            glob.assert_not_called()


@mock.patch('cachito.workers.scm.Git.clone_and_archive')
def test_fetch_source_clone_if_no_archive_yet(mock_clone_and_archive):
    scm_git = scm.Git(url, ref)

    po = mock.patch.object
    with po(scm_git.sources_dir.archive_path, 'exists', return_value=False):
        with po(scm_git.sources_dir.package_dir, 'glob', return_value=[]):
            scm_git.fetch_source()

    mock_clone_and_archive.assert_called_once()


@mock.patch('os.path.getctime')
@mock.patch('cachito.workers.scm.Git.update_and_archive')
def test_fetch_source_by_pull(mock_update_and_archive, mock_getctime):
    mock_getctime.side_effect = [
        datetime(2020, 3, 1, 20, 0, 0).timestamp(),
        datetime(2020, 3, 4, 10, 13, 30).timestamp(),
    ]

    scm_git = scm.Git(url, ref)

    po = mock.patch.object
    with po(scm_git.sources_dir.archive_path, 'exists', return_value=False):
        with po(
            scm_git.sources_dir.package_dir, 'glob',
            return_value=['29eh2a.tar.gz', 'a8c2d2.tar.gz']
        ):
            scm_git.fetch_source()

    mock_update_and_archive.assert_called_once_with('a8c2d2.tar.gz')


@mock.patch('tarfile.open')
@mock.patch('tempfile.TemporaryDirectory')
@mock.patch('git.Repo')
def test_update_and_archive(mock_repo, mock_temp_dir, mock_tarfile_open):
    # Mock the archive being created
    mock_tarfile = mock.Mock()
    mock_tarfile_open.return_value.__enter__.return_value = mock_tarfile

    # Mock the tempfile.TemporaryDirectory context manager
    mock_temp_dir.return_value.__enter__.return_value = '/tmp/cachito-temp'

    # Test does not really extract this archive file. The filename could be arbitrary.
    scm.Git(url, ref).update_and_archive('/tmp/1234567.tar.gz')

    # Verify the tempfile.TemporaryDirectory context manager was used
    mock_temp_dir.return_value.__enter__.assert_called_once()

    repo = mock_repo.return_value
    # Verify the changes are pulled.
    repo.remote.return_value.fetch.assert_called_once()
    # Verify the repo is reset to specific ref
    repo.commit.assert_called_once_with(ref)
    assert repo.commit.return_value == repo.head.reference
    repo.head.reset.assert_called_once_with(index=True, working_tree=True)

    mock_tarfile.add.assert_called_once_with(mock_repo.return_value.working_dir, 'app')


@mock.patch('tarfile.open')
@mock.patch('git.Repo')
def test_update_and_archive_pull_error(mock_repo, mock_tarfile_open):
    repo = mock_repo.return_value
    repo.remote.return_value.fetch.side_effect = IOError

    with pytest.raises(CachitoError, match='Failed to fetch from the remote Git repository'):
        scm.Git(url, ref).update_and_archive('/tmp/1234567.tar.gz')
