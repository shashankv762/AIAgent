# AIAgent

## Environment Setup

API keys are **never** hardcoded in source files. They are loaded from a `.env` file that is excluded from version control via `.gitignore`.

### Getting started

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in your real keys:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   HINDSIGHT_API_KEY=your_hindsight_api_key_here
   ```

3. **Never commit `.env` to Git.** It is already listed in `.gitignore`.