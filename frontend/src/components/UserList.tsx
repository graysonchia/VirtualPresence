import { Languages, UserRound } from "lucide-react";

import type { EnrolledUser } from "../types";

interface UserListProps {
  users: EnrolledUser[];
  loading: boolean;
}

export function UserList({ users, loading }: UserListProps) {
  return (
    <section className="rounded-[2rem] border border-ink/10 bg-white/70 p-6 backdrop-blur">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-fern">
            Directory
          </p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">
            Enrolled people
          </h2>
        </div>
        <span className="rounded-full bg-mist px-3 py-1 text-xs font-semibold text-ink/60">
          {users.length}
        </span>
      </div>

      <div className="space-y-3">
        {loading && (
          <p className="py-8 text-center text-sm text-ink/50">Loading people…</p>
        )}
        {!loading && users.length === 0 && (
          <div className="rounded-2xl border border-dashed border-ink/15 px-5 py-8 text-center">
            <UserRound className="mx-auto h-6 w-6 text-ink/35" />
            <p className="mt-2 text-sm text-ink/55">
              Your first enrollment will appear here.
            </p>
          </div>
        )}
        {users.map((user) => (
          <article
            key={user.id}
            className="flex items-center gap-3 rounded-2xl border border-ink/5 bg-white p-3.5"
          >
            <div className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-lime font-display font-bold text-ink">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">
                {user.name}
              </p>
              <p className="truncate text-xs text-ink/45">{user.email}</p>
            </div>
            <span className="flex items-center gap-1 text-xs font-medium uppercase text-ink/45">
              <Languages className="h-3.5 w-3.5" />
              {user.preferred_language}
            </span>
          </article>
        ))}
      </div>
    </section>
  );
}

