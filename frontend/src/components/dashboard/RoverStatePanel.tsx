import { Activity } from "lucide-react";
import DashboardPanel from "./DashboardPanel";

type RoverState = "exploring" | "sampling" | "returning" | "idle" | "charging";

const stateConfig: Record<RoverState, { label: string; colorClass: string; bgClass: string }> = {
  exploring: { label: "EXPLORING", colorClass: "text-primary", bgClass: "bg-primary/20" },
  sampling: { label: "SAMPLING", colorClass: "text-accent", bgClass: "bg-accent/20" },
  returning: { label: "RETURNING", colorClass: "text-warning", bgClass: "bg-warning/20" },
  idle: { label: "IDLE", colorClass: "text-muted-foreground", bgClass: "bg-muted" },
  charging: { label: "CHARGING", colorClass: "text-success", bgClass: "bg-success/20" },
};

const RoverStatePanel = () => {
  const currentState: RoverState = "exploring";
  const config = stateConfig[currentState];

  const stats = [
    { label: "Battery", value: "78%", status: "nominal" },
    { label: "Signal", value: "-42 dBm", status: "nominal" },
    { label: "Speed", value: "0.12 m/s", status: "nominal" },
    { label: "Temp", value: "-23°C", status: "warning" },
    { label: "Uptime", value: "14d 7h", status: "nominal" },
    { label: "Distance", value: "847m", status: "nominal" },
  ];

  return (
    <DashboardPanel
      title="Rover State"
      icon={<Activity className="w-4 h-4" />}
      statusIndicator={
        <div className="flex items-center gap-2">
          <span className={`inline-block w-2 h-2 rounded-full ${config.bgClass} animate-pulse-glow`} />
          <span className={`font-mono text-xs tracking-wider ${config.colorClass}`}>
            {config.label}
          </span>
        </div>
      }
    >
      <div className="space-y-4">
        <div className={`flex items-center justify-center py-6 rounded-md ${config.bgClass} border border-border`}>
          <div className="text-center">
            <div className={`font-display text-2xl font-bold tracking-wider ${config.colorClass} text-glow-primary`}>
              {config.label}
            </div>
            <div className="font-mono text-xs text-muted-foreground mt-1">
              MODE ACTIVE · SOL 47
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {stats.map((stat) => (
            <div key={stat.label} className="bg-secondary/30 rounded px-2.5 py-2 border border-border">
              <div className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider">
                {stat.label}
              </div>
              <div className={`font-mono text-sm font-semibold mt-0.5 ${
                stat.status === "warning" ? "text-warning" : "text-foreground"
              }`}>
                {stat.value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </DashboardPanel>
  );
};

export default RoverStatePanel;
