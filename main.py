import argparse
import os
import requests
import json
import pathspec
import subprocess
import re

gpt4 = "gpt-4"
codellama = "codellama:34b"


def get_github_token():
    try:
        # Execute the command to get the token status
        result = subprocess.run(["gh", "auth", "status", "--show-token"], check=True, capture_output=True, text=True)
        stdout = result.stdout

        # Parse the output to extract the token
        token_match = re.search(r'✓ Token: (\S+)', stdout)
        if token_match:
            token = token_match.group(1)
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
    gitignore_path = os.path.join(directory, '.gitignore')
    if not os.path.exists(gitignore_path):
        return None
    with open(gitignore_path, 'r') as file:
        spec = pathspec.PathSpec.from_lines('gitwildmatch', file)
    return spec


def is_source_code(file):
    source_code_extensions = ['.py', '.js', '.java', '.cpp', '.c', '.cs', '.ts', '.php', '.rb', '.go']
    _, ext = os.path.splitext(file)
    return ext in source_code_extensions


def process_directory(directory, model_name, api_url, token, organization):
    responses = []
    gitignore_spec = read_gitignore(directory)
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not is_hidden(os.path.join(root, d))]
        for file in files:
            file_path = os.path.join(root, file)
            if is_source_code(file) and (not gitignore_spec or not gitignore_spec.match_file(file_path)):
                response = process_file(file_path, model_name, api_url, token, organization)
                response = response if response else "None"
                summary = "#Summary for " + file_path + ":\n" + response + "\n\n"
                responses.append(summary)
    return responses


def process_file(filepath, model_name, api_url, token, organization):
    with open(filepath, 'r') as file:
        file_content = file.read()
    prompt = "Summarize this code by identifying important functions and classes. Ignore all helper functions, built in calls, and focus just on the most important code. Conciseness matters."

    if model_name != gpt4:
        prompt += "  Here is the code:\n\n " + file_content

    print("=================================================================")
    print("Processing file: ", filepath)
    print("Prompt is ", prompt)

    # Number of retries
    retries = 1
    while retries >= 0:
        try:
            one_minute = 60

            if token is not None:
                response = requests.post(api_url, json={"model": model_name, "prompt": prompt, "code": file_content,
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
                        print(json_response["analysis"], end='', flush=True)
                        accumulated_response += json_response.get("analysis", "")
                        return accumulated_response
                    else:
                        print(json_response["response"], end='', flush=True)

                        accumulated_response += json_response.get("response", "")
                        if json_response.get("done", False):
                            return accumulated_response
            break  # Break out of the loop if successful

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            retries -= 1
            if retries < 0:
                print("Retrying failed, no more attempts left.")
                return None

    return accumulated_response


def main():
    parser = argparse.ArgumentParser(description="Process files for summarization")
    parser.add_argument("file_or_directory", nargs='?', default=os.getcwd())

    # model can be codellama:34b or gpt-4
    parser.add_argument("--model", default=codellama)
    parser.add_argument("--organization", nargs='?')
    parser.add_argument("--api_url", default="http://localhost:11434/api/generate")
    parser.add_argument("--output", nargs='?')

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

    if model_name == gpt4:
        token = get_github_token()
        api_url = 'http://127.0.0.1:8000/customprocess'
    else:
        api_url = args.api_url
        token = None

    if isDirectory:
        responses = process_directory(directory, model_name, api_url, token, organization)
    else:
        responses = process_file(file, model_name, api_url, token, organization)

    print('Responses are')
    print(responses)
    if args.output:
        output = args.output
    else:
        if isDirectory:
            output = os.path.join(directory, 'apispec.md')
        else:
            output = os.path.join(file + '.apispec.md')
        output = 'apispec.md'

    with open(output, 'w') as outfile:
        # responses is a string, just write it to the file
        # responses is an array, make it a string and write it to the file
        data = '\n'.join(responses)
        outfile.write(data)
        # json.dump(responses, outfile)


if __name__ == "__main__":
    main()
