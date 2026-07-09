import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertOctagon, RefreshCw } from "lucide-react";
import "./ErrorBoundary.css";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
  info: ErrorInfo | null;
}

/// Last-resort catch for renderer crashes. Without it, a thrown React
/// error blanks the Tauri window with no signal to the user; with it,
/// they see the error, the component stack, and a Reload button.
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null, info: null };

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ info });
    console.error("ErrorBoundary caught:", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      const stack =
        this.state.info?.componentStack ?? this.state.error.stack ?? "";
      return (
        <div className="error-boundary">
          <div className="error-boundary-card">
            <div className="error-boundary-header">
              <AlertOctagon size={22} />
              <h1>Something broke.</h1>
            </div>
            <p className="error-boundary-message">{this.state.error.message}</p>
            {stack && (
              <details className="error-boundary-details">
                <summary>Details</summary>
                <pre>{stack}</pre>
              </details>
            )}
            <button
              type="button"
              className="btn btn-primary"
              onClick={this.handleReload}
            >
              <RefreshCw size={14} />
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
