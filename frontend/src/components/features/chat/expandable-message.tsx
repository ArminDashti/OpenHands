import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { code } from "../markdown/code";
import { ol, ul } from "../markdown/list";
import ArrowUp from "#/icons/angle-up-solid.svg?react";
import ArrowDown from "#/icons/angle-down-solid.svg?react";
import CheckCircle from "#/icons/check-circle-solid.svg?react";
import XCircle from "#/icons/x-circle-solid.svg?react";

interface ExpandableMessageProps {
  id?: string;
  message: string;
  type: string;
  success?: boolean;
}

export function ExpandableMessage({
  id,
  message,
  type,
  success,
}: ExpandableMessageProps) {
  const { t, i18n } = useTranslation();
  const [showDetails, setShowDetails] = useState(true);
  const [headline, setHeadline] = useState("");
  const [details, setDetails] = useState(message);

  useEffect(() => {
    if (id && i18n.exists(id)) {
      // Only show the headline if the action hasn't been executed yet (success is undefined)
      if (success === undefined) {
        setHeadline(t(id));
        setDetails("");
        setShowDetails(false);
      } else {
        // Only show the details if the action has been executed
        setHeadline("");
        setDetails(message);
        setShowDetails(true);
      }
    } else {
      // If no translation ID is provided, just show the message
      setHeadline("");
      setDetails(message);
      setShowDetails(true);
    }
  }, [id, message, success, i18n.language, t]);

  const arrowClasses = "h-4 w-4 ml-2 inline fill-neutral-300";
  const statusIconClasses = "h-4 w-4 ml-2 inline";

  return (
    <div className="flex gap-2 items-center justify-between border-l-2 border-neutral-300 pl-2 my-2 py-2">
      <div className="text-sm leading-4 flex flex-col gap-2 max-w-full">
        {headline && (
          <p className="text-neutral-300 font-bold">
            {headline}
            <button
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              className="cursor-pointer text-left"
            >
              {showDetails ? (
                <ArrowUp className={arrowClasses} />
              ) : (
                <ArrowDown className={arrowClasses} />
              )}
            </button>
          </p>
        )}
      </div>
      {type === "action" && success !== undefined && (
        <div className="flex-shrink-0">
          {success ? (
            <CheckCircle
              data-testid="status-icon"
              className={`${statusIconClasses} fill-success`}
            />
          ) : (
            <XCircle
              data-testid="status-icon"
              className={`${statusIconClasses} fill-danger`}
            />
          )}
        </div>
      )}
    </div>
  );
}
