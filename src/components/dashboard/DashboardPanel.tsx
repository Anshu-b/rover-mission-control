import { ReactNode } from "react";

interface DashboardPanelProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  statusIndicator?: ReactNode;
}

const DashboardPanel = ({ title, icon, children, className = "", statusIndicator }: DashboardPanelProps) => {
  return (
    <div className={`relative bg-card border border-border rounded-lg overflow-hidden border-glow ${className}`}>
      <div className="scanline pointer-events-none absolute inset-0 z-10" />
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-secondary/30">
        <div className="flex items-center gap-2">
          {icon && <span className="text-primary">{icon}</span>}
          <h3 className="font-display text-xs tracking-widest uppercase text-primary">
            {title}
          </h3>
        </div>
        {statusIndicator}
      </div>
      <div className="p-4 relative z-0">
        {children}
      </div>
    </div>
  );
};

export default DashboardPanel;
