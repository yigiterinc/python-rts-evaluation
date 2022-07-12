import os
import logging
from git import Repo

from ttictoc import tic, toc

target_folders = ["boto3"]

CSV_HEADERS = ["Iteration", "Time taken without RTS", "Number of Changed Files", "Percentage of Selected Tests",
               "Time taken with RTS", "Saved Time", "Ratio (with/without RTS)"]


log = logging.getLogger()
log.setLevel(logging.DEBUG)

NUMBER_OF_COMMITS_TO_CHECK = 20


def init():
    # iterate over target_folders
    for folder in target_folders:
        os.chdir(folder)

        measure_testing_times_in_commit_history(folder)

        os.chdir("..")


def measure_testing_times_in_commit_history(folder):
    __cleanup()

    # write headers to csv file if it doesn't exist
    if os.path.exists(f"../{folder}-output.csv"):
        # delete file
        os.remove(f"../{folder}-output.csv")

    write_csv_headers(folder)

    global NUMBER_OF_COMMITS_TO_CHECK

    repo = Repo(os.getcwd())

    commit_ids = []
    # iterate over commits
    for commit in repo.iter_commits('master', max_count=NUMBER_OF_COMMITS_TO_CHECK, reverse=True, no_merges=True):
        commit_ids.append(commit.hexsha)

    # checkout to commit_ids[0]
    repo.git.checkout(commit_ids[0])
    run_test_suite_build_mapping_database()
    counter = 1
    while counter < len(commit_ids):
        commit_id = commit_ids[counter]
        logging.info(f"Iter: {counter}, Commit id: {commit_id}")

        os.system(f"git cherry-pick -n {commit_id}")
        logging.info(f"Applied commit {commit_id}")

        change_list_names = get_changelist_of_commit(repo)
        number_of_changed_files = len(change_list_names)
        # log changed file names
        logging.info("Changed files: " + str(change_list_names))

        # run git diff --cached
        logging.info("Git status")
        os.system("git status")

        # Run tests and note how much time it took
        tic()
        os.system("pytest --junitxml=retest-all.xml -q")

        # Calculate the time it took to run the tests
        time_taken = toc()
        log.info("Time taken to run tests without RTS: " + str(time_taken))

        # Run tests with RTS and note how much time it took
        tic()
        # --co
        os.system(f"pytest --rts --rts-coverage-db=pytest-rts-coverage -q --junitxml=rts.xml")
        time_taken_with_rts = toc()
        # Calculate the time it took to run the tests
        log.info("Time taken to run tests with RTS: " + str(time_taken_with_rts))
        number_of_selected_tests = 0

        saved_time = time_taken - time_taken_with_rts
        log.info("Saved time: " + str(saved_time))

        if time_taken == 0:
            log.info("Time taken is 0, skipping...")
            return

        # Ratio
        ratio = time_taken_with_rts / time_taken
        log.info("Ratio: " + str(ratio))

        # Write to file
        write_to_csv_file(folder, f"{counter},{time_taken},"
                                  f"{number_of_changed_files}, {number_of_selected_tests},"
                                  f"{time_taken_with_rts},{saved_time},{ratio}")

        # Clean up
        # git reset hard
        os.system("git reset --hard")
        os.system("git restore --staged .")
        # get current position of head
        repo.git.checkout(commit_id, force=True)
        counter += 1

    calculate_average_statistics(folder)


def get_changelist_of_commit(repo):
    changed_file_names = [item.a_path for item in repo.index.diff('Head')]
    return changed_file_names


def write_csv_headers(folder):
    with open(f"../{folder}-output.csv", "a") as f:
        f.write(",".join(CSV_HEADERS))
        f.write("\n")


def write_to_csv_file(folder, what_to_write):
    with open(f"../{folder}-output.csv", "a") as f:
        f.write(what_to_write)
        f.write("\n")


def calculate_average_statistics(folder_path):
    AVERAGE_STATISTICS = {
        "file": folder_path,
        "average_time_taken_without_rts": 0,
        "average_time_taken_with_rts": 0,
        "average_saved_time": 0,
        "average_ratio": 0,
        "average_nr_of_selected_tests": 0,
        "average_nr_of_changed_files": 0
    }

    with open(f"../{folder_path}-output.csv", "r") as f:
        lines = f.readlines()
        for idx, line in enumerate(lines):
            if idx == 0:
                continue

            line = line.split(",")
            AVERAGE_STATISTICS["average_time_taken_without_rts"] += float(line[1])
            AVERAGE_STATISTICS["average_nr_of_changed_files"] += float(line[2])
            AVERAGE_STATISTICS["average_nr_of_selected_tests"] += float(line[3])
            AVERAGE_STATISTICS["average_time_taken_with_rts"] += float(line[4])
            AVERAGE_STATISTICS["average_saved_time"] += float(line[5])
            AVERAGE_STATISTICS["average_ratio"] += float(line[6])

    AVERAGE_STATISTICS["average_time_taken_without_rts"] /= len(lines)
    AVERAGE_STATISTICS["average_time_taken_with_rts"] /= len(lines)
    AVERAGE_STATISTICS["average_saved_time"] /= len(lines)
    AVERAGE_STATISTICS["average_ratio"] /= len(lines)
    AVERAGE_STATISTICS["average_nr_of_selected_tests"] /= len(lines)
    AVERAGE_STATISTICS["average_nr_of_changed_files"] /= len(lines)

    # write to a new file
    with open(f"../average_statistics.csv", "w") as f:
        # write headers
        f.write(",".join(AVERAGE_STATISTICS.keys()))
        # write values using f string and \n
        f.write(
            f"\n{AVERAGE_STATISTICS['file']},"
            f"{AVERAGE_STATISTICS['average_time_taken_without_rts']},"
            f"{AVERAGE_STATISTICS['average_nr_of_changed_files']},"
            f"{AVERAGE_STATISTICS['average_nr_of_selected_tests']},"
            f"{AVERAGE_STATISTICS['average_time_taken_with_rts']},"
            f"{AVERAGE_STATISTICS['average_saved_time']},"
            f"{AVERAGE_STATISTICS['average_ratio']}"
        )


def run_test_suite_build_mapping_database():
    log.info("Running test suite and generating coverage db...")
    # print current path
    log.info("Attempting to run tests at: " + os.getcwd())

    # run command in folder
    try:
        os.system("pytest --cov=. --cov-context=test --cov-config=.coveragerc")
        # rename coverage files
        os.system("mv .coverage pytest-rts-coverage")
    except Exception as e:
        print("ERROR: Unexpected error: Could not run tests")


def __cleanup():
    log.info("Cleaning up the coverage db...")
    # checkout to master
    os.system("git checkout master -f")
    # delete file
    if os.path.exists("pytest-rts-coverage"):
        os.remove("pytest-rts-coverage")


    print("Done cleaning up the coverage dbs...")


if __name__ == '__main__':
    # os.chdir(target_folders[0])
    # calculate_average_statistics("aws-dynamodb-encryption-python")
    init()
