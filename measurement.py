import os
import logging
from git import Repo

target_folders = [{'folder_name': "aws-dynamodb-encryption-python", 'tests_folder': 'test'}]
                  #{'folder_name': "PyBoy", 'tests_folder': 'tests'}



def generate_coverage_dbs():
    # iterate over target_folders
    for folder in target_folders:
        folder_name = folder['folder_name']
        tests_folder = folder['tests_folder']
        os.chdir(f"{folder_name}/{tests_folder}")

        measure_testing_times_in_commit_history()

        os.chdir("../..")

    __cleanup()


def measure_testing_times_in_commit_history():
    # run command in folder
    run_test_suite_build_mapping_database()

    # move to parent folder
    os.chdir("..")

    # Find commit id of 19 commits back
    repo = Repo(os.getcwd())
    commits = repo.iter_commits('master', max_count=20)
    commit_id = next(commits).hexsha
    # print commit id
    logging.info("Commit id: " + commit_id)

    # Checkout to commit id
    repo.git.checkout(commit_id)

    # Apply the next commit after commit_id
    repo.git.cherry_pick(next(commits).hexsha)

    # Run tests and note how much time it took
    start_time = os.times()
    os.system("pytest")
    end_time = os.times()


def run_test_suite_build_mapping_database():
    logging.info("Running test suite and generating coverage db...")
    # print current path
    logging.info("Attempting to run tests at: " + os.getcwd())
    # run command in folder
    try:
        os.system("pytest --cov=. --cov-context=test --cov-config=.coveragerc")
    except Exception as e:
        print("ERROR: Unexpected error: Could not run tests")


def __cleanup():
    logging.info("Cleaning up the coverage dbs...")
    # iterate over target_folders
    for folder in target_folders:
        folder_name = folder['folder_name']
        # move to folder
        os.chdir(folder_name)
        # delete file
        if os.path.exists(".coverage"):
            os.remove(".coverage")
        # move back to parent folder
        os.chdir("..")

    print("Done cleaning up the coverage dbs...")


if __name__ == '__main__':
    generate_coverage_dbs()
    run_test_suite_build_mapping_database()
