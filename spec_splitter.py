import re
import argparse


def read_and_split_summaries(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Split content by '#Summary for' but keep the delimiter
    summaries = re.split(r'(?=#Summary for)', content)

    return summaries


def write_individual_summaries(summaries):
    for summary in summaries:
        # Extract the file path
        match = re.search(r'#Summary for (.*):', summary)
        if match:
            file_path = match.group(1)
            # Generate new file name
            new_file_name = f"{file_path}.aispec.md"
            with open(new_file_name, 'w') as file:
                file.write(summary)
                print(f"Written summary to {new_file_name}")


def main(input_file):
    summaries = read_and_split_summaries(input_file)
    write_individual_summaries(summaries)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a file containing summaries and split into individual files.")
    parser.add_argument("input_file", help="Path to the input file containing summaries")
    args = parser.parse_args()

    main(args.input_file)
