import streamlit as st
from pathlib import Path
from ollama import chat
from git import Repo
import tempfile
import shutil



st.set_page_config(
    page_title="AI Repository Bug Detector",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Repository Bug Detector")
st.write(
    "Enter a GitHub repository URL and let AI scan the repository "
    "for potential issues, explain the problems, and suggest fixes."
)


repo_url = st.text_input(
    "🔗 GitHub Repository URL",
    placeholder="https://github.com/owner/repository"
)



def clone_repository(url):

    temp_dir = tempfile.mkdtemp()

    try:

        Repo.clone_from(
            url,
            temp_dir,
            depth=1
        )

        return Path(temp_dir)

    except Exception as e:

        shutil.rmtree(
            temp_dir,
            ignore_errors=True
        )

        return None


def find_python_files(repo_path):

    ignored_directories = {
        ".git",
        "venv",
        ".venv",
        "__pycache__",
        "node_modules",
        "dist",
        "build",
        ".idea",
        ".vscode"
    }

    python_files = []

    for file in repo_path.rglob("*.py"):

        if any(
            directory in ignored_directories
            for directory in file.parts
        ):
            continue

        python_files.append(file)

    return python_files



def read_file(file):

    try:

        return file.read_text(
            encoding="utf-8"
        )

    except UnicodeDecodeError:

        try:

            return file.read_text(
                encoding="latin-1"
            )

        except Exception:

            return None

    except Exception:

        return None



def analyze_file(file_path, code, relative_path):

    prompt = f"""
You are an expert Python code reviewer.

We are analyzing a real GitHub repository.

===== FILE =====

{relative_path}


===== CODE =====

{code}


===== TASK =====

Analyze this file for potential bugs or correctness problems.

Look for things such as:

- Runtime errors
- Incorrect logic
- Missing error handling
- Unsafe assumptions
- Incorrect conditions
- Incorrect calculations
- Unhandled edge cases
- Resource handling problems
- Clearly broken code

IMPORTANT:

1. Only report a problem if there is reasonable evidence in the code.
2. Do not invent bugs.
3. Do not report style issues unless they can cause a real problem.
4. Do not modify the code.
5. If the file appears correct, say NO_ISSUES.

If you find an issue, return EXACTLY this format:

ISSUE:
<short description>

SEVERITY:
LOW / MEDIUM / HIGH / CRITICAL

FUNCTION:
<function or class name>

ROOT_CAUSE:
<explanation>

SUGGESTED_FIX:
<explanation>

TEST:
<test that should verify the fix>

If there is no meaningful issue, return:

NO_ISSUES
"""

    try:

        response = chat(
            model="llama3.2",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.message.content

    except Exception as e:

        return f"ERROR: {str(e)}"



def generate_fix(file_path, code, analysis, relative_path):

    prompt = f"""
You are an expert Python software engineer.

A potential issue was detected in this file.

===== FILE =====

{relative_path}


===== CURRENT CODE =====

{code}


===== ANALYSIS =====

{analysis}


===== TASK =====

Provide a corrected version of this file.

Rules:

1. Fix only the issue identified above.
2. Do not unnecessarily rewrite the file.
3. Preserve unrelated functionality.
4. Do not invent dependencies.
5. Return ONLY the corrected Python code.
6. Do not use Markdown code fences.
"""

    try:

        response = chat(
            model="llama3.2",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        return response.message.content

    except Exception as e:

        return f"ERROR: {str(e)}"



if st.button("🔍 Analyze Repository"):

    if not repo_url.strip():

        st.warning(
            "Please enter a GitHub repository URL."
        )

        st.stop()



    with st.spinner(
        "📦 Cloning GitHub repository..."
    ):

        repo_path = clone_repository(
            repo_url.strip()
        )


    if repo_path is None:

        st.error(
            "❌ Could not clone the repository. "
            "Check that the URL is correct and the repository is public."
        )

        st.stop()


    st.success(
        "✅ Repository cloned successfully!"
    )



    python_files = find_python_files(
        repo_path
    )


    st.subheader("📂 Repository Scan")

    st.write(
        f"Found **{len(python_files)} Python files**."
    )


    if not python_files:

        st.warning(
            "No Python files were found in this repository."
        )

        st.stop()



    with st.expander("📄 View scanned files"):

        for file in python_files:

            relative_path = file.relative_to(
                repo_path
            )

            st.write(
                f"• {relative_path}"
            )


    # --------------------------------------------------------
    # ANALYZE FILES
    # --------------------------------------------------------

    st.subheader("🧠 AI Code Analysis")

    issues = []

    progress = st.progress(0)

    status = st.empty()

    total_files = len(
        python_files
    )


    for index, file in enumerate(
        python_files
    ):

        relative_path = file.relative_to(
            repo_path
        )

        status.write(
            f"Analyzing `{relative_path}`..."
        )


        code = read_file(
            file
        )


        if code is None:

            continue


        if len(code) > 30000:

            status.write(
                f"Skipping very large file: `{relative_path}`"
            )

            continue


        analysis = analyze_file(
            file,
            code,
            relative_path
        )


        if (
            analysis
            and "NO_ISSUES" not in analysis
            and not analysis.startswith("ERROR:")
        ):

            issues.append(
                {
                    "file": str(relative_path),
                    "code": code,
                    "analysis": analysis
                }
            )


        progress.progress(
            (index + 1) / total_files
        )


    status.empty()



    st.subheader("🐛 Potential Issues")


    if not issues:

        st.success(
            "🎉 No potential issues were detected."
        )

    else:

        st.warning(
            f"⚠️ {len(issues)} potential issue(s) detected."
        )

        for index, item in enumerate(
            issues,
            start=1
        ):

            st.markdown(
                f"## 🐛 Issue #{index}"
            )

            st.write(
                f"**📄 File:** `{item['file']}`"
            )

            st.markdown(
                item["analysis"]
            )



            with st.spinner(
                f"🛠️ Generating fix for {item['file']}..."
            ):

                fix = generate_fix(
                    item["file"],
                    item["code"],
                    item["analysis"],
                    item["file"]
                )


            st.markdown(
                "### 🛠️ Proposed Fix"
            )

            st.code(
                fix,
                language="python"
            )


            filename = Path(
                item["file"]
            ).name


            st.download_button(

                label=f"⬇️ Download Fix for {filename}",

                data=fix,

                file_name=f"fixed_{filename}",

                mime="text/plain",

                key=f"download_{index}"
            )


            st.divider()

    shutil.rmtree(
        repo_path,
        ignore_errors=True
    )

    st.success(
        "✅ Repository analysis completed."
    )

