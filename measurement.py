import os
import logging
from git import Repo

from ttictoc import tic, toc

target_folders = ["aws-dynamodb-encryption-python"]

CSV_HEADERS = ["Iteration", "Time taken without RTS", "Time taken with RTS", "Saved Time", "Ratio (with/without RTS)"]

log = logging.getLogger()
log.setLevel(logging.DEBUG)

NUMBER_OF_COMMITS_TO_CHECK = 19


def init():
    # iterate over target_folders
    for folder in target_folders:
        os.chdir(folder)

        measure_testing_times_in_commit_history(folder)

        os.chdir("..")


def measure_testing_times_in_commit_history(folder):
    __cleanup()

    # write headers to csv file if it doesn't exist
    if not os.path.exists("../output.csv"):
        write_csv_headers()

    global NUMBER_OF_COMMITS_TO_CHECK

    # Find commit id of 19 commits back
    repo = Repo(os.getcwd())

    try:
        while NUMBER_OF_COMMITS_TO_CHECK > 0:
            commits = repo.iter_commits('master', max_count=NUMBER_OF_COMMITS_TO_CHECK)
            commit_id = next(commits).hexsha
            # print commit id
            logging.info(f"Iter: {20 - NUMBER_OF_COMMITS_TO_CHECK}, Commit id: {commit_id}")

            # Checkout to commit id
            repo.git.checkout(commit_id)

            commit_id_of_next_commit = next(commits).hexsha

            # Apply the next commit after commit_id with --continue using os
            os.system(f"git cherry-pick {commit_id_of_next_commit}")

            logging.info(f"Applied commit {commit_id_of_next_commit}")
            logging.info("Printing git staged file names")
            os.system("git diff --cached --name-only")
            diff_list = repo.head.commit.diff()
            # log diff list
            for diff in diff_list:
                logging.info(f"{diff.a_path}")

            run_test_suite_build_mapping_database()

            # Run tests and note how much time it took
            tic()
            os.system("pytest -q")

            # Calculate the time it took to run the tests
            time_taken = toc()
            log.info("Time taken to run tests without RTS: " + str(time_taken))

            # Run tests with RTS and note how much time it took
            tic()
            os.system("pytest -q --rts --rts-coverage-db=.coverage")
            time_taken_with_rts = toc()
            # Calculate the time it took to run the tests
            log.info("Time taken to run tests with RTS: " + str(time_taken_with_rts))

            # Gain of time
            saved_time = time_taken - time_taken_with_rts
            log.info("Gain of time: " + str(saved_time))


            if time_taken == 0:
                log.info("Time taken is 0, skipping...")
                return

            # Ratio
            ratio = time_taken_with_rts / time_taken
            log.info("Ratio: " + str(ratio))

            # Write to file
            write_to_csv_file(f"{20 - NUMBER_OF_COMMITS_TO_CHECK},{time_taken},{time_taken_with_rts},{saved_time},{ratio}")

            NUMBER_OF_COMMITS_TO_CHECK -= 1
    except StopIteration:
        log.info("No more commits to check")

    calculate_average_statistics(folder)


def write_csv_headers():
    with open("../output.csv", "a") as f:
        f.write(",".join(CSV_HEADERS))
        f.write("\n")


def write_to_csv_file(what_to_write):
    with open("../output.csv", "a") as f:
        f.write(what_to_write)
        f.write("\n")


def calculate_average_statistics(folder_path):
    AVERAGE_STATISTICS = {
        "file": folder_path,
        "average_time_taken_without_rts": 0,
        "average_time_taken_with_rts": 0,
        "average_saved_time": 0,
        "average_ratio": 0
    }

    with open("../output.csv", "r") as f:
        lines = f.readlines()
        for line in lines:
            line = line.split(",")
            AVERAGE_STATISTICS["average_time_taken_without_rts"] += float(line[1])
            AVERAGE_STATISTICS["average_time_taken_with_rts"] += float(line[2])
            AVERAGE_STATISTICS["average_saved_time"] += float(line[3])
            AVERAGE_STATISTICS["average_ratio"] += float(line[4])

    AVERAGE_STATISTICS["average_time_taken_without_rts"] /= len(lines)
    AVERAGE_STATISTICS["average_time_taken_with_rts"] /= len(lines)
    AVERAGE_STATISTICS["average_saved_time"] /= len(lines)
    AVERAGE_STATISTICS["average_ratio"] /= len(lines)

    # write to a new file
    with open("../average_statistics.csv", "w") as f:
        # write headers
        f.write(",".join(AVERAGE_STATISTICS.keys()))
        # write values using f string and \n
        f.write(
            f"\n{AVERAGE_STATISTICS['average_time_taken_without_rts']},"
            f"{AVERAGE_STATISTICS['average_time_taken_with_rts']},"
            f"{AVERAGE_STATISTICS['average_saved_time']},"
            f"{AVERAGE_STATISTICS['average_ratio']}")


def run_test_suite_build_mapping_database():
    log.info("Running test suite and generating coverage db...")
    # print current path
    log.info("Attempting to run tests at: " + os.getcwd())

    # run command in folder
    try:
        os.system("pytest --cov=. --cov-context=test --cov-config=.coveragerc")
    except Exception as e:
        print("ERROR: Unexpected error: Could not run tests")


def __cleanup():
    log.info("Cleaning up the coverage db...")
    # delete file
    if os.path.exists(".coverage"):
        os.remove(".coverage")

    print("Done cleaning up the coverage dbs...")


if __name__ == '__main__':
    init()
