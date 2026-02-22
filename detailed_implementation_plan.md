Complete Implementation Plan — AI-Powered Test Case Generator
(Code Upload/Paste + Flexible Prompt-Driven Test Generation)

extra cases:
i want the option for the user to upload the code file or just paste the code into llm and then ask for instructions or just normal prompt for test code generation, eg user uploads/paste code and ask to generate code to test if this code's functions and all are working, or generate test cases for the uploaded code so user can use their to run tests to see their code is doing what its supposed to do or no

What the User Experience Actually Looks Like
The user arrives at the app and sees two sections. The top section is the code input — either a file upload button or a paste area. The bottom section is a prompt box. They fill in both and hit generate.
Some real examples of what a user might type in the prompt box after uploading their code:

"Generate unit tests for all functions in this file"
"Generate tests only for the authenticate_user function"
"Generate tests that check edge cases like empty inputs and null values"
"Generate integration tests that test how these functions work together"
"Generate tests and also tell me if there are any obvious bugs in my code"
"Generate pytest test cases I can run locally"
"Generate Jest tests for this JavaScript file"

The prompt is what gives the user control. Without it, the system has to guess what they want. With it, the output is targeted and actually useful to them.

How the Architecture Handles This
When both code and a prompt arrive at your backend together, your agent needs to do three things in sequence before generating anything.
First, it parses the code using AST (for Python) or a similar parser to extract the function signatures, dependencies, and structure. This happens automatically regardless of what the user typed in the prompt — you always want this structural understanding.
Second, it reads the user's prompt and classifies the intent. Is the user asking for unit tests, integration tests, edge case tests, or a specific function's tests? This classification step is just a quick LLM call with a simple prompt asking it to extract: test type, target scope (all functions vs specific ones), target framework if mentioned, and any special requirements mentioned. This structured extraction then guides the generation step.
Third, it combines the extracted code structure with the classified intent and runs the actual test generation prompt. The generation prompt now has both the "what" (from the code analysis) and the "how" (from the prompt classification), which is what produces genuinely useful output.

How the Prompt Changes the Generation
This is the key technical insight. Your test generation prompt template should have placeholder slots that get filled differently based on what the user asked for.
If the user said "generate edge case tests," the prompt instructs the LLM to focus on boundary values, null inputs, empty strings, zero values, and type mismatches. If the user said "generate integration tests," the prompt shifts to testing how functions call each other and what the end-to-end behavior is. If the user named a specific function, the prompt filters the code analysis down to just that function's context. If the user mentioned a specific framework like PyTest or Jest, that gets injected into the prompt as a hard requirement.
The user's free-text prompt essentially becomes a set of configuration parameters for your generation template. You're not passing their raw text to the LLM as-is — you're extracting the intent from it and using that to build a precise, structured generation prompt. This produces far more consistent output than just appending their message to a generic prompt.

Preparation Week — Before Any Code
Spend two to three days doing nothing but reading and experimenting. Open your LLM playground and manually test prompts with real code snippets. Paste a Python function and try prompting it with "generate edge case tests," then "generate integration tests," then "generate only tests for the authenticate function" — observe how the output differs and what instructions produce clean, runnable output vs messy output. This experimentation directly informs your prompt templates later and saves you enormous debugging time.
Read the Python ast module documentation thoroughly. Understand how to walk an AST tree, extract function names, parameters, return annotations, decorators, and docstrings. Practice writing a small standalone script that takes any Python file and prints out every function's name and signature. This becomes your code parser.
Read the PyTest documentation on fixtures, parametrize, mocking with unittest.mock, and pytest-cov. You need to know what a well-structured test file looks like before you can instruct an LLM to write one.
Set up your GitHub repository from day one with a clean branch strategy — main for stable working code, dev for active development. Set up your project board with each phase as a card. The commit history you build over this project is visible to recruiters and tells a story about how you work.

Project Folder Architecture
Plan and create this structure before writing any logic:
Your root contains requirements.txt, .env.example, README.md, docker-compose.yml, and the .github/workflows folder. Inside the project you have five packages. backend contains your FastAPI application, database models, and API routes. agent contains all LangChain logic split into subfolders for prompts, chains, tools, and parsers. processor contains the input handling layer — the code parser, the prompt intent classifier, and the file handler. frontend contains the Streamlit application. generated_tests is where output test files land, organized by language and feature name.
This separation matters because a modularized project looks like a system. A flat folder of scripts looks like a homework assignment.

Phase 1: Database & API Foundation (Days 1–2)
Database Schema
Set up SQLite with SQLAlchemy. You need two tables. The first is a generation_jobs table storing: job ID, timestamp, input mode (upload or paste), original filename if uploaded, detected language, the user's raw prompt, the classified intent extracted from that prompt, the generated test code, quality score, and job status. The second is a test_run_results table storing: job ID, pass count, fail count, error count, coverage percentage, CI run URL, and run timestamp. Having this from the start means your history feature costs almost nothing to build later.
FastAPI Application Setup
Create your main FastAPI app with CORS configured for your Streamlit frontend's address. Set up environment variable loading from .env using python-dotenv. Configure a logger that writes to both console and a rotating log file — every request, every LLM call, and every test run should be logged with enough detail that you can debug any failure after the fact.
Pydantic Request and Response Models
Define these before writing any endpoint. Your generation request model has five fields: input_mode (an enum: paste or upload), code_content (the raw code as a string), filename (optional, used when uploaded), language (enum: python, javascript, typescript, java), and user_prompt (the free-text instruction from the user). Your response model has: job_id, generated_test_code, quality_score, uncovered_areas (a list of strings), warnings (a list of strings flagged during parsing), and framework_used.
Defining these upfront forces you to think through the entire data flow before writing a single chain or endpoint, and keeps everything consistent end to end.
API Endpoints
You need four endpoints to start. A POST /generate that accepts the generation request and returns the response model. A GET /jobs that returns the history list for the sidebar. A GET /jobs/{job_id} that returns full detail for a specific past job. A POST /jobs/{job_id}/rerun that re-executes the test file and updates the run results. Keep each endpoint thin — all real logic lives in the agent and processor layers, not in the route handlers.

Phase 2: The Input Processing Layer (Days 3–5)
This layer sits between the raw user input and the LangChain agent. Its entire job is to normalize whatever the user provides into a clean, structured object the agent can work with consistently.
File Upload Handler
Streamlit sends uploaded files as binary streams. Your handler reads the content as UTF-8 text, extracts the filename and extension, maps the extension to a language using a dictionary you maintain (.py → Python, .js → JavaScript, .ts → TypeScript, .java → Java, etc.), enforces a file size limit of around 50KB to avoid hitting LLM context limits, and rejects unsupported extensions with a clear error message. For supported files, it returns the text content and detected language. Treat a file upload and a paste identically after this point — downstream code should never need to know which input method was used.
Python Code Parser
For Python files or pastes, use the ast module to walk the syntax tree and extract structured metadata. For every function in the file, you want to capture: the function name, the parameter names and their type annotations if present, the return type annotation if present, the docstring if present, any decorators (which can indicate things like @staticmethod, @property, or framework decorators), and every external name the function references that isn't defined in the same file (these are your dependency candidates for mocking). Store this as a list of function metadata objects.
This structured extraction is what lets you display the function selector in the UI and is also what dramatically improves the quality of your generation prompt — you're giving the LLM precise structural information rather than making it re-read the entire file every time.
JavaScript/TypeScript Code Parser
You can't use Python's ast module for JS/TS. Instead, use a lightweight approach: send the raw code to the LLM in a quick preliminary call with a simple prompt asking it to return a JSON list of function names, parameters, and whether each function has external dependencies. This is a fast, cheap call — you're not generating tests yet, just extracting structure. Store the result the same way you store Python's AST output so everything downstream is uniform.
Prompt Intent Classifier
This is a new component that doesn't exist in the original plan and is central to making the flexible prompt approach work well. When the user's prompt arrives, before doing anything with the code, run a small LLM call that reads the prompt and extracts five things: the test type requested (unit, integration, edge case, or a mix), the target scope (all functions, specific named functions, or a specific area of functionality), the target framework if explicitly mentioned (PyTest, unittest, Jest, Mocha), any special requirements (like "include mocks," "don't use fixtures," "add comments explaining each test"), and a confidence score indicating how clear the instruction was.
Return these five fields as a structured JSON object. If the confidence is low — meaning the prompt was vague — flag it so the UI can show a gentle suggestion asking the user to be more specific, without blocking them from proceeding. This classification output then gets passed directly into your test generation prompt template as parameters, which is what makes the generated tests actually reflect what the user asked for.
Keeping this as a separate LLM call rather than bundling it with generation is important. It's a small, fast call that makes the main generation call significantly better and easier to debug independently.
The Unified Context Object
After both the code parser and prompt intent classifier have run, assemble a single unified context object. This object contains: the raw code, the detected language, the structured function metadata from parsing, the classified intent from the prompt classifier, the original user prompt (kept for display purposes), and any warnings generated during parsing (like "three external imports detected — mocking recommended"). This is the only thing your LangChain agent receives. The agent layer never touches raw user input directly — it only ever sees this clean, structured context.

Phase 3: LangChain Agent — Test Generation Core (Days 6–11)
This is the most complex phase and deserves the most time. Plan for things taking longer than expected here.
Prompt Templates — One Per Test Type
Maintain separate prompt templates for each major test type rather than trying to handle everything in one giant prompt. You need a unit test template, an edge case test template, an integration test template, and a mixed template that combines elements of the others. Each template has placeholder slots for: the code being tested, the specific functions to target, the framework to use, the mocking instructions derived from detected dependencies, and any special requirements from the user's prompt.
The intent classifier's output fills these slots automatically. If the user asked for edge case tests, the edge case template gets loaded and its specific instructions — focus on boundary values, null inputs, empty collections, type mismatches, and off-by-one errors — shape the generation. If the user asked for unit tests, the unit test template's instructions — isolate each function, mock all external calls, test one behavior per test function — take over. This slot-filling approach is what makes your output consistently well-structured regardless of what the user typed.
The Two-Step Generation Chain
Never generate tests in a single LLM call. Use two chained calls for every generation request.
The first call is the analysis step. It receives the unified context object and produces a detailed analysis of each target function: what it does, what it's supposed to return for valid inputs, what it should do for invalid inputs, what external systems it touches, and what the most important behaviors to test are. This analysis is written in plain English, not code. Its output is stored as part of the job record and is also displayed to the user as a "what we're testing" summary before they see the generated code.
The second call is the generation step. It receives both the original unified context object and the analysis from the first step, and produces the actual test file. Because the model has already reasoned through the code in the first step, the generated tests are far more accurate and comprehensive. The generation prompt is explicit about file structure: one test class per source function, a descriptive name for every test method, a docstring on each test explaining what behavior it's verifying, proper setup and teardown using the appropriate framework conventions.
This two-step approach consistently produces better output than a single call and gives you two natural points to log, debug, and display intermediate results to the user.
Dependency Mocking — Automatic and Transparent
When the code parser identifies external imports or references, the generation prompt should explicitly instruct the LLM to generate the appropriate mock setup for each one. For Python this means unittest.mock.patch decorators and MagicMock instances. For JavaScript this means jest.mock calls at the top of the test file.
Show these mocking decisions to the user explicitly in the UI — "We detected that your code calls requests.get and database.connect — these have been automatically mocked in the generated tests." This transparency helps developers who are new to mocking understand what was done and why, and it makes your tool genuinely educational rather than just mechanical.
The Validation and Auto-Correction Loop
After generation, run a syntax check using Python's compile() function for Python code or a simple parse check for JS. If the syntax is invalid, feed the error message back to the LLM with the broken code and ask it to fix only the syntax error without changing the test logic. Allow up to two correction attempts. After two failed attempts, return the output to the user with the error clearly highlighted and a note explaining where the problem is. Never silently fail.
Log every correction attempt with the error message and the corrected output. Display this iteration history in the UI as a small collapsible "generation log" — it shows the user that the system self-corrects and adds credibility to the output.
The Self-Evaluation Step
After successful validation, run one final LLM call that evaluates the generated test file against five criteria: does it test the happy path, does it test error conditions, does it cover edge cases, are mocks used correctly, and are assertions specific and meaningful. Each criterion scores 0 to 2, giving a maximum quality score of 10. Also have this step return a short list of what's not covered — "no test for concurrent access," "timeout behavior not tested," "no test for the case where the database is unavailable." Display the score as a badge and the gaps as improvement suggestions.
This self-evaluation is one of the most impressive features in the project because it turns a passive generator into something that actively reflects on its own output.

Phase 4: File System & CI/CD Integration (Days 12–14)
File System Organization
Write generated test files to generated_tests/{language}/{feature_name}/test_{feature_name}.py. Use the original filename (stripped of extension) as the feature name when a file was uploaded, or derive it from the first function name when code was pasted. Alongside every test file, write a metadata JSON file with the same base name storing: job ID, generation timestamp, input mode, quality score, framework used, and the list of uncovered areas. This metadata is what the history sidebar reads.
GitHub Actions Workflow
Create a workflow that triggers on every push to main. It installs dependencies, runs pytest with coverage on the entire generated_tests folder, writes results to a JSON artifact, and posts a commit status back to GitHub. Also add a pull request trigger for when the auto-commit feature is used.
For surfacing CI results in your UI, use the GitHub REST API. When a test file is committed, store the commit SHA in your database. Poll the Actions API for that SHA every ten seconds until the run completes, then update the status in your database and push the update to the Streamlit frontend using session state refresh.
Auto-Commit Toggle
Add an optional "Commit to GitHub automatically" toggle in the UI. When enabled and the syntax check passes, use GitPython to stage and commit the generated test file to the repository, which triggers the GitHub Actions run. This creates the full cinematic pipeline loop: user pastes code, types a prompt, hits generate, watches the test file appear, sees the CI badge go from "Running" to "Passed." That moment is the centerpiece of your demo video.

Phase 5: Streamlit Frontend (Days 15–17)
Layout and Information Hierarchy
The main area has three vertical sections. The top section is the code input — a tab switcher between "Paste Code" and "Upload File." Below that is the prompt section — a text area with placeholder text giving the user example prompts they can use. Below that is the options panel and the generate button. After generation, a results section appears below the generate button showing the analysis summary, the generated code viewer, the quality score, and the CI status.
Code Input Area
For paste mode, use a streamlit-ace editor component set to the detected language for syntax highlighting. For upload mode, show a file uploader that accepts .py, .js, .ts, and .java files. After a file is uploaded, automatically display its content in a read-only ace editor so the user can see what was uploaded before generating. Show the detected language and a list of detected functions as a multiselect below the editor — the user can deselect functions they don't want tests generated for.
Prompt Box with Suggestions
The prompt text area should have helper text that disappears when the user starts typing, showing three example prompts: "Generate unit tests for all functions," "Generate edge case tests for the validate_input function," "Generate pytest tests with mocks for all external dependencies." These suggestions dramatically reduce friction for users who aren't sure what to type and make the tool more approachable in a demo.
Below the prompt box, after the intent classifier runs, show a small "We understood this as: Unit tests targeting all functions using PyTest" confirmation line. This builds trust and lets the user correct any misclassification before generation proceeds.
Results Section
Show four panels after generation. The analysis summary panel shows the plain-English analysis from the first LLM call — what each function does and what behaviors will be tested. The code viewer panel shows the generated test file in a syntax-highlighted ace editor that the user can edit before saving. The quality panel shows the score out of 10 and the list of uncovered areas. The CI panel shows the run status with a live-updating badge and a link to the GitHub Actions run page.
Add a "Regenerate with Different Prompt" button that clears the results and puts focus back on the prompt box without clearing the code input. This is a small UX detail that makes the tool feel polished and practical.
History Sidebar
A left sidebar lists all past generation jobs sorted by most recent. Each entry shows the filename or a truncated first line of pasted code, the language, the quality score, the framework, and the last CI status. Clicking a history entry loads the full job detail into the main view including the original code, the original prompt, and the generated tests. Add a "Re-run Tests" button on history entries so the user can re-execute the test file without regenerating.

Phase 6: Deployment (Days 18–19)
Docker Setup
Write a docker-compose.yml with two services — one for FastAPI and one for Streamlit — sharing a volume for the generated_tests directory. Both services should read from the same .env file. Test that the entire project starts with a single docker compose up command. This is important because interviewers who want to run your project locally will do exactly that, and it needs to work cleanly.
Cloud Deployment
Deploy FastAPI to Railway or Render on their free tier. Deploy Streamlit to Streamlit Community Cloud. Document the environment variables needed in your .env.example file and in the README so anyone can configure their own deployment. Make sure your live demo URL is in your README and your resume.

Phase 7: README, Demo Video & Polish (Days 20–21)
README Structure
Open with one paragraph describing the problem and your solution. Follow with the architecture diagram. Then a feature list written from the user's perspective ("Upload any Python or JavaScript file, describe the tests you want in plain English, and get a runnable test suite in seconds"). Then installation instructions, a live demo link, and a demo video embed. Add GitHub Actions build badge and Python version badge at the top.