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

const CHART_COLORS = ["#18d6bd", "#5b6ff9", "#7c3aed", "#f59e0b"];

type ChartPoint = {
  label: string;
  value: number;
};

type ChartCardProps = {
  title: string;
  data: ChartPoint[];
};

export function BarChartCard({ title, data }: ChartCardProps) {
  return (
    <div className="chart-card">
      <h4>{title}</h4>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(255 255 255 / 12%)" />
          <XAxis dataKey="label" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip />
          <Bar dataKey="value" fill="#18d6bd" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function LineChartCard({ title, data }: ChartCardProps) {
  return (
    <div className="chart-card">
      <h4>{title}</h4>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(255 255 255 / 12%)" />
          <XAxis dataKey="label" stroke="#94a3b8" />
          <YAxis stroke="#94a3b8" />
          <Tooltip />
          <Line type="monotone" dataKey="value" stroke="#5b6ff9" strokeWidth={3} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function PieChartCard({ title, data }: ChartCardProps) {
  return (
    <div className="chart-card">
      <h4>{title}</h4>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="label" cx="50%" cy="50%" outerRadius={88} label>
            {data.map((entry, index) => (
              <Cell key={entry.label} fill={CHART_COLORS[index % CHART_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
