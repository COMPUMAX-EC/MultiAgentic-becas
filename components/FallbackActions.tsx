type FallbackActionsProps = {
  onTryAgain?: () => void;
  onLoadLatestDemo?: () => void;
  onUseMockResults?: () => void;
  isTryingAgain?: boolean;
  isLoadingDemo?: boolean;
};

export function FallbackActions({
  onTryAgain,
  onLoadLatestDemo,
  onUseMockResults,
  isTryingAgain = false,
  isLoadingDemo = false,
}: FallbackActionsProps) {
  return (
    <div className="fallback-actions">
      {onTryAgain ? (
        <button
          className="secondary-action"
          type="button"
          onClick={onTryAgain}
          disabled={isTryingAgain || isLoadingDemo}
        >
          {isTryingAgain ? "Trying again..." : "Try again"}
        </button>
      ) : null}
      {onLoadLatestDemo ? (
        <button
          className="secondary-action"
          type="button"
          onClick={onLoadLatestDemo}
          disabled={isTryingAgain || isLoadingDemo}
        >
          {isLoadingDemo ? "Loading latest demo..." : "Load latest demo results"}
        </button>
      ) : null}
      {onUseMockResults ? (
        <button
          className="secondary-action"
          type="button"
          onClick={onUseMockResults}
          disabled={isTryingAgain || isLoadingDemo}
        >
          Use sample results
        </button>
      ) : null}
    </div>
  );
}
