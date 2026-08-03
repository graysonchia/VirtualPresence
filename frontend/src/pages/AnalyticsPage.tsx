import {
  Activity,
  BrainCircuit,
  Clock3,
  LoaderCircle,
  ScanFace,
  ShieldCheck,
  ShieldX,
  UsersRound,
} from "lucide-react";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ApiError } from "../api/client";
import { AppHeader } from "../components/AppHeader";
import type { AppView } from "../components/AppHeader";
import {
  useAnalyticsOverview,
  useEmotionDistribution,
  useRecognitionTrends,
  useUsagePatterns,
} from "../hooks/useAnalyticsApi";

interface AnalyticsPageProps {
  onNavigate: (view: AppView) => void;
}

const CHART_COLORS = [
  "#226f54",
  "#ff7a59",
  "#8abf52",
  "#5b7cfa",
  "#f2b84b",
  "#8b5cf6",
  "#3ea7a0",
];

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} sec`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(1)} min`;
  return `${(minutes / 60).toFixed(1)} hr`;
}

function formatDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError
    ? error.message
    : "Analytics could not be loaded.";
}

interface StatCardProps {
  label: string;
  value: string;
  detail: string;
  icon: typeof Activity;
  accent?: "fern" | "coral";
}

function StatCard({
  label,
  value,
  detail,
  icon: Icon,
  accent = "fern",
}: StatCardProps) {
  return (
    <article className="rounded-3xl border border-white/70 bg-white/75 p-5 shadow-sm backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink/40">
            {label}
          </p>
          <p className="mt-3 font-display text-3xl font-semibold text-ink">
            {value}
          </p>
          <p className="mt-1 text-xs text-ink/45">{detail}</p>
        </div>
        <span
          className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl ${
            accent === "coral"
              ? "bg-coral/10 text-coral"
              : "bg-fern/10 text-fern"
          }`}
        >
          <Icon className="h-4 w-4" />
        </span>
      </div>
    </article>
  );
}

interface ChartCardProps {
  title: string;
  description: string;
  children: React.ReactNode;
  className?: string;
}

function ChartCard({
  title,
  description,
  children,
  className = "",
}: ChartCardProps) {
  return (
    <section
      className={`rounded-[2rem] border border-white/70 bg-white/80 p-5 shadow-sm backdrop-blur sm:p-6 ${className}`}
    >
      <h2 className="font-display text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-1 text-xs leading-5 text-ink/45">{description}</p>
      <div className="mt-5 h-72">{children}</div>
    </section>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="grid h-full place-items-center rounded-2xl bg-mist/50 text-center text-sm text-ink/40">
      {message}
    </div>
  );
}

export function AnalyticsPage({ onNavigate }: AnalyticsPageProps) {
  const [trendDays, setTrendDays] = useState(30);
  const overview = useAnalyticsOverview();
  const recognition = useRecognitionTrends(trendDays);
  const emotions = useEmotionDistribution();
  const usage = useUsagePatterns();
  const queries = [overview, recognition, emotions, usage];
  const isLoading = queries.some((query) => query.isLoading);
  const error = queries.find((query) => query.error)?.error;

  const recognitionData =
    recognition.data?.points.map((point) => ({
      ...point,
      label: formatDate(point.date),
      confidence:
        point.average_match_confidence === null
          ? null
          : point.average_match_confidence * 100,
      liveness:
        point.liveness_pass_rate === null
          ? null
          : point.liveness_pass_rate * 100,
    })) ?? [];
  const emotionData = emotions.data?.emotions ?? [];
  const dailyUsage =
    usage.data?.daily.map((point) => ({
      ...point,
      label: formatDate(point.date),
    })) ?? [];
  const hourlyUsage =
    usage.data?.hourly.map((point) => ({
      ...point,
      label: `${point.hour.toString().padStart(2, "0")}:00`,
    })) ?? [];

  return (
    <main className="min-h-screen px-5 py-6 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-7xl">
        <AppHeader currentView="analytics" onNavigate={onNavigate} />

        <section className="pb-12 pt-8">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-fern/10 px-3 py-1.5 text-xs font-semibold text-fern">
                <Activity className="h-3.5 w-3.5" />
                Platform telemetry
              </span>
              <h1 className="mt-4 font-display text-4xl font-semibold tracking-tight text-ink sm:text-5xl">
                Analytics overview
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/50">
                Recognition quality, conversation activity, aggregate emotion,
                and memory usage from persisted VirtualPresence interactions.
              </p>
            </div>
            <label className="flex items-center gap-3 rounded-2xl border border-ink/8 bg-white/70 px-4 py-3 text-xs font-semibold text-ink/55 shadow-sm">
              Recognition window
              <select
                value={trendDays}
                onChange={(event) => setTrendDays(Number(event.target.value))}
                className="rounded-xl border border-ink/10 bg-white px-3 py-1.5 text-ink outline-none focus:border-fern"
              >
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
                <option value={90}>90 days</option>
              </select>
            </label>
          </div>

          {isLoading && !overview.data && (
            <div className="mt-10 flex min-h-72 items-center justify-center gap-2 rounded-[2rem] bg-white/65 text-sm text-ink/45 shadow-sm">
              <LoaderCircle className="h-4 w-4 animate-spin" />
              Aggregating platform activity…
            </div>
          )}

          {error && (
            <p className="mt-8 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage(error)}
            </p>
          )}

          {overview.data && (
            <>
              <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="Enrolled users"
                  value={overview.data.total_users.toLocaleString()}
                  detail={`${overview.data.total_sessions.toLocaleString()} interaction sessions`}
                  icon={UsersRound}
                />
                <StatCard
                  label="Recognition success"
                  value={formatPercent(
                    overview.data.recognition_success_rate,
                  )}
                  detail={`${overview.data.total_recognition_attempts.toLocaleString()} total attempts`}
                  icon={ScanFace}
                />
                <StatCard
                  label="Average confidence"
                  value={formatPercent(
                    overview.data.average_match_confidence,
                  )}
                  detail={`${formatPercent(overview.data.liveness_pass_rate)} pass · ${formatPercent(overview.data.liveness_fail_rate)} fail`}
                  icon={ShieldCheck}
                />
                <StatCard
                  label="Spoof detections"
                  value={overview.data.spoof_detection_count.toLocaleString()}
                  detail="Flagged recognition attempts"
                  icon={ShieldX}
                  accent="coral"
                />
                <StatCard
                  label="Messages"
                  value={overview.data.total_messages.toLocaleString()}
                  detail={`${overview.data.average_messages_per_session.toFixed(1)} per session`}
                  icon={Activity}
                />
                <StatCard
                  label="Average session"
                  value={formatDuration(
                    overview.data.average_session_length_seconds,
                  )}
                  detail="From session start to final activity"
                  icon={Clock3}
                />
                <StatCard
                  label="Memory facts"
                  value={overview.data.total_memory_facts.toLocaleString()}
                  detail={`${overview.data.referenced_memory_facts.toLocaleString()} referenced at least once`}
                  icon={BrainCircuit}
                />
                <StatCard
                  label="Facts per session"
                  value={overview.data.average_referenced_facts_per_session.toFixed(
                    2,
                  )}
                  detail="Referenced stored facts ÷ sessions"
                  icon={BrainCircuit}
                />
              </div>

              <div className="mt-6 grid gap-6 lg:grid-cols-2">
                <ChartCard
                  title="Recognition quality"
                  description={`Daily average match confidence and liveness pass rate over ${trendDays} days.`}
                  className="lg:col-span-2"
                >
                  {recognitionData.some((point) => point.total_attempts > 0) ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={recognitionData}>
                        <CartesianGrid stroke="#dfe7df" strokeDasharray="3 3" />
                        <XAxis
                          dataKey="label"
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                          minTickGap={24}
                        />
                        <YAxis
                          domain={[0, 100]}
                          tickFormatter={(value) => `${value}%`}
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                        />
                        <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                        <Legend />
                        <Line
                          type="monotone"
                          dataKey="confidence"
                          name="Match confidence"
                          stroke="#226f54"
                          strokeWidth={3}
                          dot={false}
                          connectNulls
                        />
                        <Line
                          type="monotone"
                          dataKey="liveness"
                          name="Liveness pass rate"
                          stroke="#ff7a59"
                          strokeWidth={3}
                          dot={false}
                          connectNulls
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart message="No recognition attempts in this window." />
                  )}
                </ChartCard>

                <ChartCard
                  title="Emotion distribution"
                  description="Aggregate emotions detected during recognition events; no per-message content is shown."
                >
                  {emotionData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={emotionData}
                          dataKey="count"
                          nameKey="emotion"
                          cx="50%"
                          cy="48%"
                          innerRadius={58}
                          outerRadius={95}
                          paddingAngle={3}
                        >
                          {emotionData.map((item, index) => (
                            <Cell
                              key={item.emotion}
                              fill={CHART_COLORS[index % CHART_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart message="No emotion observations yet." />
                  )}
                </ChartCard>

                <ChartCard
                  title="Daily usage"
                  description="Sessions started and messages sent on each calendar day."
                >
                  {dailyUsage.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={dailyUsage}>
                        <CartesianGrid stroke="#dfe7df" strokeDasharray="3 3" />
                        <XAxis
                          dataKey="label"
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                          minTickGap={18}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                        />
                        <Tooltip />
                        <Legend />
                        <Bar
                          dataKey="sessions"
                          name="Sessions"
                          fill="#226f54"
                          radius={[5, 5, 0, 0]}
                        />
                        <Bar
                          dataKey="messages"
                          name="Messages"
                          fill="#c8ff7c"
                          radius={[5, 5, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart message="No conversation activity yet." />
                  )}
                </ChartCard>

                <ChartCard
                  title="Activity by hour"
                  description={`Session starts and messages by hour (${usage.data?.timezone ?? "UTC"})${
                    usage.data?.most_active_hour === null ||
                    usage.data?.most_active_hour === undefined
                      ? "."
                      : `; peak session hour is ${usage.data.most_active_hour
                          .toString()
                          .padStart(2, "0")}:00.`
                  }`}
                  className="lg:col-span-2"
                >
                  {hourlyUsage.some(
                    (point) => point.sessions > 0 || point.messages > 0,
                  ) ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={hourlyUsage}>
                        <CartesianGrid stroke="#dfe7df" strokeDasharray="3 3" />
                        <XAxis
                          dataKey="label"
                          interval={2}
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fontSize: 11, fill: "#5f716a" }}
                        />
                        <Tooltip />
                        <Legend />
                        <Bar
                          dataKey="sessions"
                          name="Sessions"
                          fill="#226f54"
                          radius={[5, 5, 0, 0]}
                        />
                        <Bar
                          dataKey="messages"
                          name="Messages"
                          fill="#ff7a59"
                          radius={[5, 5, 0, 0]}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <EmptyChart message="No hourly activity is available." />
                  )}
                </ChartCard>
              </div>
            </>
          )}
        </section>
      </div>
    </main>
  );
}
