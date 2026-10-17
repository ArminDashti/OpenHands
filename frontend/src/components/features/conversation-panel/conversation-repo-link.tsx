interface ConversationRepoLinkProps {
  repo: string;
  onClick?: (event: React.MouseEvent<HTMLAnchorElement>) => void;
}

export function ConversationRepoLink({
  repo,
  onClick,
}: ConversationRepoLinkProps) {
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    window.open(
      `https://github.com/${selectedRepository}`,
      "_blank",
      "noopener,noreferrer",
    );
  };

  return (
    <a
      data-testid="conversation-card-repo"
      href={`https://github.com/${repo}`}
      target="_blank noopener noreferrer"
      onClick={onClick}
      className="text-xs text-neutral-400 hover:text-neutral-200"
    >
      {repo}
    </a>
  );
}
