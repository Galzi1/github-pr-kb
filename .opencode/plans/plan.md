# Work Plan: github-pr-kb
## TL;DR
Create a CLI tool to analyze GitHub PR comments and generate AI agent harness files.
## Context
- Analyze merged PRs with comments.
- Use personal access token for GitHub API.
- Single JSON config for important/ignored people/agents.
- Store intermediate results in a document-based DB.
- Export final results to Markdown files.
## Work Objectives
- Implement GitHub API interaction using personal access token.
- Design and implement document-based DB schema for storing agent harness files and index.
- Develop logic to analyze PR comments and generate AI agent harness files.
- Create a single command CLI interface.
## TODOs
1. **Implement GitHub API client**:
   - Use \`gh\` CLI's authentication mechanism.
   - Handle rate limiting and errors.
2. **Design document-based DB schema**:
   - Define structure for agent harness files.
   - Create index for quick lookup.
3. **Develop PR comment analysis logic**:
   - Use LLM ("openrouter/meta-llama/llama-4-maverick" with "focused") to analyze comments.
   - Generate AI agent harness files based on analysis.
4. **Implement CLI tool**:
   - Single command with options for config file and output directory.
   - Handle user input and configuration.
5. **Integrate DB operations**:
   - Store and update agent harness files in DB.
   - Maintain index for agent harness files.
6. **Export final results to Markdown files**:
   - Read final contents from DB.
   - Write to Markdown files on disk.
## Success Criteria
- CLI tool can analyze PR comments and generate AI agent harness files.
- Final results are exported correctly to Markdown files.
