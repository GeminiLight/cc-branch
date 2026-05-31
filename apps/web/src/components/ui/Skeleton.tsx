interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  circle?: boolean;
}

export default function Skeleton({
  className = "",
  width,
  height,
  circle = false,
}: SkeletonProps) {
  const style: React.CSSProperties = {};
  if (width !== undefined) style.width = typeof width === "number" ? `${width}px` : width;
  if (height !== undefined) style.height = typeof height === "number" ? `${height}px` : height;

  return (
    <div
      className={`bg-[var(--border-subtle)] animate-skeleton ${circle ? "rounded-full" : "rounded-md"} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}

export function SkeletonCard({ children }: { children?: React.ReactNode }) {
  return (
    <div className="surface-card border border-default rounded-lg p-4 space-y-3">
      {children || (
        <>
          <div className="flex items-center gap-3">
            <Skeleton width={32} height={32} circle />
            <div className="flex-1 space-y-1.5">
              <Skeleton width="60%" height={14} />
              <Skeleton width="40%" height={10} />
            </div>
          </div>
          <Skeleton width="100%" height={40} />
        </>
      )}
    </div>
  );
}
