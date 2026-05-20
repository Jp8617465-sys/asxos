Read CLAUDE.md and PROJECT_STATUS.md first.

Run a discovery audit on $ARGUMENTS (or full codebase if no arguments).

This is a READ-ONLY investigation. Do NOT modify any files.

1. Database state: query row counts and freshness for key tables
2. Service inventory: which services exist, which have tests, which are orphaned
3. Job inventory: which jobs are scheduled, which have run recently
4. Frontend components: which exist, which are tested, which are routed
5. Data pipeline health: are signals fresh? Are screen matches current?

Focus on: what's actually working vs what we assumed was working.

Output a structured report with specific numbers (row counts, dates, file paths).
Flag anything that doesn't match PROJECT_STATUS.md.
