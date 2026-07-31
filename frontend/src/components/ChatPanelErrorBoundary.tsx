import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

interface ChatPanelErrorBoundaryProps {
  children: ReactNode;
}

interface ChatPanelErrorBoundaryState {
  hasError: boolean;
}

export class ChatPanelErrorBoundary extends Component<
  ChatPanelErrorBoundaryProps,
  ChatPanelErrorBoundaryState
> {
  state: ChatPanelErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ChatPanelErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ChatPanel crashed", error, errorInfo);
  }

  private retry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <section
          className="rounded-[2.5rem] border border-amber-200 bg-white p-7 text-center shadow-panel sm:p-9"
          role="alert"
        >
          <h2 className="font-display text-xl font-semibold text-ink">
            Conversation temporarily unavailable
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink/55">
            The chat panel ran into a problem. The rest of VirtualPresence is
            still available.
          </p>
          <button
            type="button"
            onClick={this.retry}
            className="mt-5 rounded-xl bg-ink px-4 py-2 text-sm font-semibold text-lime transition hover:bg-fern"
          >
            Try chat again
          </button>
        </section>
      );
    }

    return this.props.children;
  }
}
