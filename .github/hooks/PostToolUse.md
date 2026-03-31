# AutoTeam Copilot CLI Hook — Post-Tool Use

After every Write or Edit operation, prompt to update pipeline status if phase changed.

## After Write tool (if pipeline is active)

If you modified a file in `.autoteam/workspace/`, check if the pipeline phase should be updated and prompt user.
