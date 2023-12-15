import json
import os
import argparse


def combine_markdown_files(json_file, max_files=None):
    with open(json_file, 'r') as file:
        data = json.load(file)

    combined_content = ""
    files = data.get("files", {})

    file_count = 0
    for filename in files:
        if max_files is not None and file_count >= max_files:
            break
        md_filename = filename + ".aispec.md"
        if os.path.exists(md_filename):
            with open(md_filename, 'r') as md_file:
                combined_content += md_file.read() + "\n\n"
            file_count += 1

    output_file = f'aispec_combined_prioritized_{max_files}.md' if max_files is not None else 'aispec_combined_prioritized.md'
    with open(output_file, 'w') as outfile:
        outfile.write(combined_content)
    print(f"Combined markdown written to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Combine markdown files based on a prioritized list from a JSON file.")
    parser.add_argument("json_file", help="Path to the JSON file containing the list of filenames")
    parser.add_argument("--max_files", type=int, default=None, help="Maximum number of files to process (optional)")
    args = parser.parse_args()

    combine_markdown_files(args.json_file, args.max_files)


if __name__ == "__main__":
    main()
