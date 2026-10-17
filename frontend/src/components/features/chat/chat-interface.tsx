import React from "react";
import posthog from "posthog-js";
import { convertImageToBase64 } from "#/utils/convert-image-to-base-64";
import { FeedbackActions } from "../feedback/feedback-actions";
import { createChatMessage } from "#/services/chat-service";
import { InteractiveChatBox } from "./interactive-chat-box";
import { RootState } from "#/store";
import AgentState from "#/types/agent-state";
import { generateAgentStateChangeEvent } from "#/services/agent-state-service";
import { useScrollToBottom } from "#/hooks/use-scroll-to-bottom";
import { TypingIndicator } from "./typing-indicator";
import { useWsClient } from "#/context/ws-client-provider";
import { Messages } from "./messages";
import { ChatSuggestions } from "./chat-suggestions";
import { ActionSuggestions } from "./action-suggestions";
import { ContinueButton } from "#/components/shared/buttons/continue-button";
import { ScrollToBottomButton } from "#/components/shared/buttons/scroll-to-bottom-button";
import { LoadingSpinner } from "#/components/shared/loading-spinner";

function getEntryPoint(
  hasRepository: boolean | null,
  hasImportedProjectZip: boolean | null,
): string {
  if (hasRepository) return "github";
  if (hasImportedProjectZip) return "zip";
  return "direct";
}

export function ChatInterface() {
  const { send, isLoadingMessages } = useWsClient();
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const { scrollDomToBottom, onChatBodyScroll, hitBottom } =
    useScrollToBottom(scrollRef);

  // Use the chat context instead of Redux
  const { messages, addUserMessage } = useChatContext();
  // Use the agent state context instead of Redux
  const { curAgentState } = useAgentStateContext();

  // Trigger auto-scroll when new messages arrive or agent state changes
  React.useEffect(() => {
    if (messages.length > 0 && scrollRef.current) {
      scrollDomToBottom();
    }
  }, [messages.length, curAgentState, scrollDomToBottom]);

  const [messageToSend, setMessageToSend] = React.useState<string | null>(null);
  const { selectedRepository, importedProjectZip } = useSelector(
    (state: RootState) => state.initalQuery,
  );

  const handleSendMessage = async (content: string, files: File[]) => {
    console.log("ChatInterface - handleSendMessage called with content:", content);
    
    if (messages.length === 0) {
      posthog.capture("initial_query_submitted", {
        entry_point: getEntryPoint(
          selectedRepository !== null,
          importedProjectZip !== null,
        ),
        query_character_length: content.length,
        uploaded_zip_size: importedProjectZip?.length,
      });
    } else {
      posthog.capture("user_message_sent", {
        session_message_count: messages.length,
        current_message_length: content.length,
      });
    }
    const promises = images.map((image) => convertImageToBase64(image));
    const imageUrls = await Promise.all(promises);

    const timestamp = new Date().toISOString();
    const pending = true;
    // Use the context function instead of dispatching to Redux
    addUserMessage({ content, imageUrls, timestamp, pending });
    send(createChatMessage(content, imageUrls, timestamp));
    setMessageToSend(null);
  };

  const handleStop = () => {
    posthog.capture("stop_button_clicked");
    send(generateAgentStateChangeEvent(AgentState.STOPPED));
  };

  const handleSendContinueMsg = () => {
    handleSendMessage("Continue", []);
  };

  const onClickShareFeedbackActionButton = async (
    polarity: "positive" | "negative",
  ) => {
    setFeedbackModalIsOpen(true);
    setFeedbackPolarity(polarity);
  };

  const isWaitingForUserInput =
    agentState === AgentState.AWAITING_USER_INPUT ||
    agentState === AgentState.FINISHED;

  // If in setup mode, show setup progress instead of regular chat
  if (isSetupMode && conversationId) {
    return <ConversationSetupFlow conversationId={conversationId} />;
  }

  return (
    <div className="h-full flex flex-col justify-between">
      {messages.length === 0 && (
        <ChatSuggestions onSuggestionsClick={setMessageToSend} />
      )}

      <div
        ref={scrollRef}
        onScroll={(e) => onChatBodyScroll(e.currentTarget)}
        className="flex flex-col grow overflow-y-auto overflow-x-hidden px-4 pt-4 gap-2"
      >
        {isLoadingMessages && (
          <div className="flex justify-center">
            <LoadingSpinner size="small" />
          </div>
        )}

        {!isLoadingMessages && (
          <Messages
            messages={messages}
            isAwaitingUserConfirmation={
              agentState === AgentState.AWAITING_USER_CONFIRMATION
            }
          />
        )}

        {isWaitingForUserInput && (
          <ActionSuggestions
            onSuggestionsClick={(value) => handleSendMessage(value, [])}
          />
        )}
      </div>

      <div className="flex flex-col gap-[6px] px-4 pb-4">
        <div className="flex justify-between relative">
          <FeedbackActions
            onPositiveFeedback={() =>
              onClickShareFeedbackActionButton("positive")
            }
            onNegativeFeedback={() =>
              onClickShareFeedbackActionButton("negative")
            }
          />

          <div className="absolute left-1/2 transform -translate-x-1/2 bottom-0">
            {messages.length > 2 &&
              curAgentState === AgentState.AWAITING_USER_INPUT && (
                <ContinueButton onClick={handleSendContinueMsg} />
              )}
            {curAgentState === AgentState.RUNNING && <TypingIndicator />}
          </div>

          {!hitBottom && <ScrollToBottomButton onClick={scrollDomToBottom} />}
        </div>

        <InteractiveChatBox
          onSubmit={handleSendMessage}
          onStop={handleStop}
          isDisabled={
            agentState === AgentState.LOADING ||
            agentState === AgentState.AWAITING_USER_CONFIRMATION
          }
          mode={curAgentState === AgentState.RUNNING ? "stop" : "submit"}
          value={messageToSend ?? ""}
          onChange={setMessageToSend}
        />
      </div>
    </div>
  );
}
