import { useMemo } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { usePaginatedConversations } from "#/hooks/query/use-paginated-conversations";
import { Conversation } from "#/api/open-hands.types";
import { ConversationStatus } from "#/types/conversation-status";
import { cn } from "#/utils/utils";
import { formatTimeDelta } from "#/utils/format-time-delta";
import { GitProviderIcon } from "#/components/shared/git-provider-icon";
import { Provider } from "#/types/settings";
import CodeBranchIcon from "#/icons/u-code-branch.svg?react";
import RepoForkedIcon from "#/icons/repo-forked.svg?react";
import { LoadingSpinner } from "#/components/shared/loading-spinner";

type KanbanColumn = {
  status: ConversationStatus;
  label: I18nKey;
  bgColor: string;
  borderColor: string;
  dotColor: string;
};

const KANBAN_COLUMNS: KanbanColumn[] = [
  {
    status: "STARTING",
    label: I18nKey.COMMON$STARTING,
    bgColor: "bg-yellow-500/10",
    borderColor: "border-yellow-500/30",
    dotColor: "bg-[#FFD43B]",
  },
  {
    status: "RUNNING",
    label: I18nKey.COMMON$RUNNING,
    bgColor: "bg-green-500/10",
    borderColor: "border-green-500/30",
    dotColor: "bg-[#1FBD53]",
  },
  {
    status: "STOPPED",
    label: I18nKey.COMMON$STOPPED,
    bgColor: "bg-neutral-500/10",
    borderColor: "border-neutral-500/30",
    dotColor: "bg-[#3C3C49]",
  },
  {
    status: "ERROR",
    label: I18nKey.COMMON$ERROR,
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    dotColor: "bg-[#FF684E]",
  },
];

interface KanbanCardProps {
  conversation: Conversation;
}

function KanbanCard({ conversation }: KanbanCardProps) {
  const { t } = useTranslation();
  const hasRepository =
    conversation.selected_repository && conversation.selected_branch;

  return (
    <Link
      to={`/conversations/${conversation.conversation_id}`}
      className="block p-3 bg-[#27272E] rounded-lg hover:bg-[#323238] transition-colors cursor-pointer border border-[#3C3C49]"
    >
      <p className="text-sm text-white font-medium mb-2 line-clamp-2">
        {conversation.title}
      </p>
      <div className="flex flex-col gap-1.5 text-xs text-[#A3A3A3]">
        {hasRepository ? (
          <div className="flex items-center gap-2">
            <GitProviderIcon
              gitProvider={conversation.git_provider as Provider}
            />
            <span
              className="truncate"
              title={conversation.selected_repository || ""}
            >
              {conversation.selected_repository}
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <RepoForkedIcon width={12} height={12} color="#A3A3A3" />
            <span>{t(I18nKey.COMMON$NO_REPOSITORY)}</span>
          </div>
        )}
        {hasRepository && (
          <div className="flex items-center gap-1">
            <CodeBranchIcon width={12} height={12} color="#A3A3A3" />
            <span
              className="truncate"
              title={conversation.selected_branch || ""}
            >
              {conversation.selected_branch}
            </span>
          </div>
        )}
        <div className="text-[#7A7A7A] mt-1">
          {formatTimeDelta(
            conversation.created_at || conversation.last_updated_at,
          )}{" "}
          {t(I18nKey.CONVERSATION$AGO)}
        </div>
      </div>
    </Link>
  );
}

interface KanbanColumnViewProps {
  column: KanbanColumn;
  conversations: Conversation[];
}

function KanbanColumnView({ column, conversations }: KanbanColumnViewProps) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col flex-shrink-0 w-72 min-w-72">
      <div
        className={cn(
          "flex items-center gap-2 px-3 py-2 rounded-t-lg border-b",
          column.bgColor,
          column.borderColor,
        )}
      >
        <div className={cn("w-2 h-2 rounded-full", column.dotColor)} />
        <h3 className="text-sm font-semibold text-white">{t(column.label)}</h3>
        <span className="text-xs text-[#A3A3A3] ml-auto">
          {conversations.length}
        </span>
      </div>
      <div
        className={cn(
          "flex flex-col gap-2 p-2 rounded-b-lg border border-t-0 min-h-[200px] max-h-[calc(100vh-220px)] overflow-y-auto custom-scrollbar",
          column.borderColor,
          "bg-[#1E1E24]",
        )}
      >
        {conversations.length === 0 ? (
          <div className="flex items-center justify-center h-24 text-xs text-[#7A7A7A]">
            {t(I18nKey.KANBAN$NO_CONVERSATIONS)}
          </div>
        ) : (
          conversations.map((conversation) => (
            <KanbanCard
              key={conversation.conversation_id}
              conversation={conversation}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default function KanbanView() {
  const { t } = useTranslation();
  const {
    data: conversationsList,
    isFetching,
    error,
  } = usePaginatedConversations(100);

  const conversations = useMemo(
    () => conversationsList?.pages.flatMap((page) => page.results) ?? [],
    [conversationsList],
  );

  const groupedConversations = useMemo(() => {
    const grouped: Record<ConversationStatus, Conversation[]> = {
      STARTING: [],
      RUNNING: [],
      STOPPED: [],
      ERROR: [],
      ARCHIVED: [],
    };

    for (const conversation of conversations) {
      const { status } = conversation;
      if (status in grouped) {
        grouped[status].push(conversation);
      }
    }

    return grouped;
  }, [conversations]);

  const isInitialLoading = isFetching && !conversationsList;

  return (
    <div className="flex flex-col h-full p-6 bg-transparent">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {t(I18nKey.KANBAN$TITLE)}
          </h1>
          <p className="text-sm text-[#A3A3A3] mt-1">
            {t(I18nKey.KANBAN$DESCRIPTION)}
          </p>
        </div>
        <Link
          to="/"
          className="px-4 py-2 text-sm font-medium text-white bg-[#27272E] rounded-lg hover:bg-[#323238] transition-colors border border-[#3C3C49]"
        >
          {t(I18nKey.KANBAN$BACK_TO_HOME)}
        </Link>
      </div>

      {error && (
        <div className="flex items-center justify-center h-64">
          <p className="text-danger">{error.message}</p>
        </div>
      )}

      {isInitialLoading && (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="large" />
        </div>
      )}

      {!isInitialLoading && !error && (
        <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
          {KANBAN_COLUMNS.map((column) => (
            <KanbanColumnView
              key={column.status}
              column={column}
              conversations={groupedConversations[column.status]}
            />
          ))}
        </div>
      )}
    </div>
  );
}
