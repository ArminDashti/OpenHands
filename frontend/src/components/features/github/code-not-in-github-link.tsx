import React from "react";
import { useCreateConversation } from "#/hooks/mutation/use-create-conversation";

const INITIAL_PROMPT = "";

export function CodeNotInGitHubLink() {
  const { mutate: createConversation } = useCreateConversation();

  const handleStartFromScratch = () => {
    // Set the initial prompt and create a new conversation
    dispatch(setInitialPrompt(INITIAL_PROMPT));
    createConversation({ q: INITIAL_PROMPT, allowEmptyQuery: true });
  };

  return (
    <div className="text-xs text-neutral-400">
      Code not in GitHub?{" "}
      <span
        onClick={handleStartFromScratch}
        className="underline cursor-pointer"
      >
        Start from scratch
      </span>{" "}
      and use the VS Code link to upload and download your code.
    </div>
  );
}
