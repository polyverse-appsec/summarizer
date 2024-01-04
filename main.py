import argparse
import os
import requests
import json
import pathspec
import subprocess
import re

gpt4 = "gpt-4"
codellama = "codellama:34b"

files_processed = 0
files_errored = 0


def get_github_token():
    try:
        # Execute the command to get the token status
        result = subprocess.run(["gh", "auth", "status", "--show-token"], check=True, capture_output=True, text=True)
        stdout = result.stdout

        # Parse the output to extract the token
        # valid strings are of the form some characters followed by a space followed by Token: followed by the token
        token_match = re.search(r'(\S+) Token: (\S+)', stdout)
        if token_match:
            token = token_match.group(2)
            return token
        else:
            print("Failed to parse GitHub token.")
            return None

    except subprocess.CalledProcessError as error:
        print(f"GitHub CLI (gh) failed authorization: {error}")
        return None


def is_hidden(filepath):
    return os.path.basename(filepath).startswith('.')


def read_gitignore(directory):
    # Function to read the contents of a file as lines
    def read_lines(filepath):
        with open(filepath, 'r') as file:
            return file.readlines()

    # Paths for the .gitignore and .boostignore files
    gitignore_path = os.path.join(directory, '.gitignore')
    boostignore_path = os.path.join(directory, '.boostignore')

    # Initialize an empty list for patterns
    patterns = []

    # Read patterns from .gitignore if it exists
    if os.path.exists(gitignore_path):
        patterns.extend(read_lines(gitignore_path))

    # Read patterns from .boostignore if it exists
    if os.path.exists(boostignore_path):
        patterns.extend(read_lines(boostignore_path))

    # Create a PathSpec from the combined patterns
    spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    return spec


def is_source_code(file):
    source_code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.ts', '.php', '.rb', '.go']
    _, ext = os.path.splitext(file)
    return ext in source_code_extensions


def process_directory(directory, model_name, api_url, token, organization, combineRawContents, verbose):
    responses = []
    gitignore_spec = read_gitignore(directory)
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not is_hidden(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            if is_source_code(file) and (not gitignore_spec or not gitignore_spec.match_file(file_path)):
                response = process_file(file_path, model_name, api_url, token, organization, combineRawContents, verbose)

                rel_path = os.path.relpath(file_path, os.getcwd())

                if response is not None:
                    global files_processed
                    files_processed += 1
                else:
                    response = "None"
                    global files_errored
                    files_errored += 1

                    # if we errored on very first attempt, then just abort - since we'll likely fail them all
                    if files_processed == 0:
                        print("Error: No files processed. Please check that the server is running and the API URL is correct.")
                        return

                if combineRawContents:
                    rawContents = "#Contents of " + rel_path + ":\n" + response + "\n\n"
                    responses.append(rawContents)
                else:
                    summary = "# Summary for " + rel_path + ":\n" + response + "\n\n"
                    responses.append(summary)

    return responses


def process_file(filepath, model_name, api_url, token, organization, combineRawContents, verbose):
    with open(filepath, 'r') as file:
        file_content = file.read()

    if combineRawContents:
        return file_content

    prompt = "Summarize this code by identifying important functions and classes. Ignore all helper functions, built in calls, and focus just on the most important code. Conciseness matters."

#     if model_name != gpt4:
    prompt += "  Here is the code:\n\n " + file_content

    if verbose:
        print("=================================================================")
    print("Processing file: ", filepath)
    if verbose:
        print("Prompt is ", prompt)

    # Number of retries
    retries = 1
    while retries >= 0:
        try:
            one_minute = 60

            if token is not None:
                # messages = [{"role": "user", "content": prompt}]
                # response = requests.post(api_url, json={"model": model_name, "messages": json.dumps(messages),  # "prompt": prompt, "code": file_content,
                #                          "session": token, "organization": organization, "version": "1.0.0"},
                #                          timeout=3 * one_minute)

                response = requests.post(api_url, json={"code": file_content,
                                         "session": token, "organization": organization, "version": "1.0.0"},
                                         timeout=3 * one_minute)
            else:
                response = requests.post(api_url, json={"model": model_name, "prompt": prompt}, stream=True, timeout=one_minute)

            accumulated_response = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    json_response = json.loads(decoded_line)

                    if model_name == gpt4:
                        if verbose:
                            print(json_response["analysis"], end='', flush=True)
                        accumulated_response += json_response.get("analysis", "")
                        return accumulated_response
                    else:
                        if verbose:
                            print(json_response["response"], end='', flush=True)

                        accumulated_response += json_response.get("response", "")
                        if json_response.get("done", False):
                            return accumulated_response
            break  # Break out of the loop if successful

        except requests.exceptions.RequestException as e:
            if verbose:
                print(f"Request failed: {e}")
            retries -= 1
            if retries < 0:
                print(f"Retrying failed, no more attempts left. Last error: {e}")
                return None

    return accumulated_response


def main():
    parser = argparse.ArgumentParser(description="Process files for summarization")
    parser.add_argument("file_or_directory", nargs='?', default=os.getcwd())

    # model can be codellama:34b or gpt-4
    parser.add_argument("--model", default=gpt4)
    parser.add_argument("--verbose", nargs='?')
    parser.add_argument("--organization", nargs='?')
    parser.add_argument("--api_url", default="http://localhost:11434/api/generate")
    parser.add_argument("--output", nargs='?')
    parser.add_argument("--rawonly", action='store_true', help="Combine raw contents only")

    args = parser.parse_args()

    arg = args.file_or_directory
    # figure out if it is a file or directory
    if os.path.isdir(arg):
        directory = arg
        isDirectory = True
    elif os.path.isfile(arg):
        file = arg
        isDirectory = False
    else:
        print("Error: file or directory not found")
        return

    organization = args.organization
    model_name = args.model
    combineRawContents = args.rawonly

    if model_name == gpt4:
        if organization is None:
            organization = "polyverse-appsec"
        token = get_github_token()
        if token is None:
            print("Error: GitHub token not found")
            return
        # api_url = 'http://127.0.0.1:8000/customprocess'
        # api_url = 'https://7ntcvdqj4r23uklomzmeiwq7nq0dhblq.lambda-url.us-west-2.on.aws/'

        # api_url = 'http://127.0.0.1:8000/codesummarizer'
        api_url = 'https://j4sijrqerxrjonxbq27hg37xte0qghrt.lambda-url.us-west-2.on.aws/'
    else:
        api_url = args.api_url
        token = None

    if isDirectory:
        responses = process_directory(directory, model_name, api_url, token, organization, combineRawContents, args.verbose)
    else:
        responses = process_file(file, model_name, api_url, token, organization, combineRawContents, args.verbose)

        if responses is not None:
            global files_processed
            files_processed += 1
        else:
            global files_errored
            files_errored += 1

    # print('Responses are')
    # print(responses)
    if args.output:
        output = args.output
    else:
        if isDirectory:
            output = os.path.join(directory, 'apispec.md')
        else:
            output = file + '.apispec.md'

    with open(output, 'w') as outfile:
        # responses is a string, just write it to the file
        # responses is an array, make it a string and write it to the file
        data = '\n'.join(responses)
        outfile.write(data)
        # json.dump(responses, outfile)


if __name__ == "__main__":
    main()
