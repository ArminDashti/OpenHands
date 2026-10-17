import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { createUsageDashboardGuard } from "#/utils/org/permission-guard";
import { useOrganizationUsage } from "#/hooks/query/use-organization-usage";
import {
  OrganizationUsageDailyConversationCount,
  OrganizationUsageRepositoryCount,
} from "#/types/org";
import { Card } from "#/ui/card";
import { Typography } from "#/ui/typography";
import { I18nKey } from "#/i18n/declaration";

const TREND_CHART_WIDTH = 720;
const TREND_CHART_HEIGHT = 220;
const TREND_CHART_PADDING = 20;

export const clientLoader = createUsageDashboardGuard();

const formatCurrency = (value: number) =>
  new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);

const formatNumber = (value: number) => new Intl.NumberFormat().format(value);

const formatShortDate = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(new Date(value));

function UsageSummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="flex-col gap-2 p-5">
      <Typography.Text className="text-xs uppercase tracking-[0.08em] text-gray-400">
        {label}
      </Typography.Text>
      <Typography.H2 className="text-3xl font-semibold text-white">
        {value}
      </Typography.H2>
    </Card>
  );
}

function UsageLoadingState() {
  return (
    <div className="flex flex-col gap-6" data-testid="usage-loading-state">
      <div className="grid gap-4 md:grid-cols-2">
        {Array.from({ length: 2 }).map((_, index) => (
          <Card
            key={index}
            className="h-28 animate-pulse rounded-xl bg-[#1F2125]"
          />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card className="h-80 animate-pulse rounded-xl bg-[#1F2125]" />
        <Card className="h-80 animate-pulse rounded-xl bg-[#1F2125]" />
      </div>
    </div>
  );
}

function UsageTrendChart({
  data,
}: {
  data: OrganizationUsageDailyConversationCount[];
}) {
  const { t } = useTranslation();
  const points = useMemo(() => {
    if (!data.length) {
      return "";
    }

    const maxCount = Math.max(
      ...data.map((item) => item.conversation_count),
      1,
    );
    const usableWidth = TREND_CHART_WIDTH - TREND_CHART_PADDING * 2;
    const usableHeight = TREND_CHART_HEIGHT - TREND_CHART_PADDING * 2;

    return data
      .map((item, index) => {
        const x =
          TREND_CHART_PADDING +
          (data.length === 1 ? 0 : (index / (data.length - 1)) * usableWidth);
        const y =
          TREND_CHART_HEIGHT -
          TREND_CHART_PADDING -
          (item.conversation_count / maxCount) * usableHeight;
        return `${x},${y}`;
      })
      .join(" ");
  }, [data]);

  const maxCount = Math.max(...data.map((item) => item.conversation_count), 1);
  const yAxisSteps = [0, 0.5, 1].map((ratio) => Math.round(maxCount * ratio));
  const firstDate = data[0]?.date;
  const lastDate = data[data.length - 1]?.date;

  return (
    <Card className="flex-col gap-5 p-5" testId="usage-trend-card">
      <div className="flex flex-col gap-1">
        <Typography.H3>{t(I18nKey.USAGE$TREND_TITLE)}</Typography.H3>
        <Typography.Text className="text-gray-400">
          {t(I18nKey.USAGE$TREND_DESCRIPTION)}
        </Typography.Text>
      </div>

      <div className="relative h-64 w-full overflow-hidden rounded-xl border border-[#3A3F4A] bg-[#1E2024] px-3 py-4">
        <svg
          viewBox={`0 0 ${TREND_CHART_WIDTH} ${TREND_CHART_HEIGHT}`}
          className="h-full w-full"
          aria-label={t(I18nKey.USAGE$TREND_TITLE)}
        >
          {yAxisSteps.map((step, index) => {
            const y =
              TREND_CHART_HEIGHT -
              TREND_CHART_PADDING -
              (step / maxCount) *
                (TREND_CHART_HEIGHT - TREND_CHART_PADDING * 2);
            return (
              <g key={`${step}-${index}`}>
                <line
                  x1={TREND_CHART_PADDING}
                  x2={TREND_CHART_WIDTH - TREND_CHART_PADDING}
                  y1={y}
                  y2={y}
                  stroke="#3A3F4A"
                  strokeDasharray="4 4"
                />
                <text
                  x={TREND_CHART_PADDING}
                  y={y - 6}
                  fill="#9CA3AF"
                  fontSize="11"
                >
                  {formatNumber(step)}
                </text>
              </g>
            );
          })}
          <polyline
            fill="none"
            stroke="#6EE7B7"
            strokeWidth="4"
            strokeLinejoin="round"
            strokeLinecap="round"
            points={points}
          />
          {data.map((item, index) => {
            const usableWidth = TREND_CHART_WIDTH - TREND_CHART_PADDING * 2;
            const usableHeight = TREND_CHART_HEIGHT - TREND_CHART_PADDING * 2;
            const x =
              TREND_CHART_PADDING +
              (data.length === 1
                ? 0
                : (index / (data.length - 1)) * usableWidth);
            const y =
              TREND_CHART_HEIGHT -
              TREND_CHART_PADDING -
              (item.conversation_count / maxCount) * usableHeight;
            return (
              <circle
                key={item.date}
                cx={x}
                cy={y}
                r="4"
                fill="#6EE7B7"
                stroke="#111827"
                strokeWidth="2"
              />
            );
          })}
        </svg>
      </div>

      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>{firstDate ? formatShortDate(firstDate) : ""}</span>
        <span>{lastDate ? formatShortDate(lastDate) : ""}</span>
      </div>
    </Card>
  );
}

function TopRepositoriesCard({
  repositories,
  emptyLabel,
  noRepositoryLabel,
}: {
  repositories: OrganizationUsageRepositoryCount[];
  emptyLabel: string;
  noRepositoryLabel: string;
}) {
  const { t } = useTranslation();
  const maxCount = Math.max(
    ...repositories.map((item) => item.conversation_count),
    1,
  );

  return (
    <Card className="flex-col gap-5 p-5" testId="usage-top-repositories-card">
      <div className="flex flex-col gap-1">
        <Typography.H3>{t(I18nKey.USAGE$TOP_REPOSITORIES_TITLE)}</Typography.H3>
        <Typography.Text className="text-gray-400">
          {t(I18nKey.USAGE$TOP_REPOSITORIES_DESCRIPTION)}
        </Typography.Text>
      </div>

      {repositories.length ? (
        <div className="flex flex-col gap-4">
          {repositories.map((repository) => (
            <div key={repository.repository} className="flex flex-col gap-2">
              <div className="flex items-center justify-between gap-3 text-sm text-white">
                <span className="truncate">
                  {repository.repository === "No repository"
                    ? noRepositoryLabel
                    : repository.repository}
                </span>
                <span className="shrink-0 text-gray-300">
                  {formatNumber(repository.conversation_count)}
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#1E2024]">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-[#6EE7B7] to-[#22C55E]"
                  style={{
                    width: `${(repository.conversation_count / maxCount) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex h-full min-h-48 items-center justify-center rounded-xl border border-dashed border-[#3A3F4A] bg-[#1E2024] px-4 text-center">
          <Typography.Text className="text-gray-400">
            {emptyLabel}
          </Typography.Text>
        </div>
      )}
    </Card>
  );
}

function UsageSettingsScreen() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useOrganizationUsage();

  if (isLoading) {
    return <UsageLoadingState />;
  }

  if (isError || !data) {
    return (
      <Card className="flex-col gap-3 p-6" testId="usage-error-state">
        <Typography.H2 className="text-xl">
          {t(I18nKey.ERROR$GENERIC)}
        </Typography.H2>
        <Typography.Text className="text-gray-400">
          {t(I18nKey.USAGE$ERROR_DESCRIPTION)}
        </Typography.Text>
      </Card>
    );
  }

  const hasConversations = data.summary.total_conversations > 0;

  return (
    <div className="flex flex-col gap-6" data-testid="usage-settings-screen">
      <div className="flex flex-col gap-1">
        <Typography.H2>{t(I18nKey.SETTINGS$NAV_USAGE)}</Typography.H2>
        <Typography.Text className="text-gray-400">
          {t(I18nKey.USAGE$PAGE_DESCRIPTION)}
        </Typography.Text>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <UsageSummaryCard
          label={t(I18nKey.USAGE$AVERAGE_COST_TITLE)}
          value={formatCurrency(
            data.summary.average_cost_per_conversation_last_30_days,
          )}
        />
        <UsageSummaryCard
          label={t(I18nKey.USAGE$TOTAL_CONVERSATIONS_TITLE)}
          value={formatNumber(data.summary.total_conversations)}
        />
      </div>

      {hasConversations ? (
        <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
          <UsageTrendChart data={data.daily_conversations} />
          <TopRepositoriesCard
            repositories={data.top_repositories}
            emptyLabel={t(I18nKey.USAGE$NO_REPOSITORIES)}
            noRepositoryLabel={t(I18nKey.USAGE$NO_REPOSITORY_LABEL)}
          />
        </div>
      ) : (
        <Card
          className="flex-col items-center gap-3 p-10 text-center"
          testId="usage-empty-state"
        >
          <Typography.H2 className="text-xl">
            {t(I18nKey.USAGE$EMPTY_TITLE)}
          </Typography.H2>
          <Typography.Text className="max-w-xl text-gray-400">
            {t(I18nKey.USAGE$EMPTY_DESCRIPTION)}
          </Typography.Text>
        </Card>
      )}
    </div>
  );
}

export default UsageSettingsScreen;
