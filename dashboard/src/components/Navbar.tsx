import { NavLink } from "react-router-dom";

type Props = { onLogout: () => void };

export default function Navbar({ onLogout }: Props) {
  return (
    <nav style={{ display: "flex", gap: 16, padding: "12px 24px", borderBottom: "1px solid #ddd" }}>
      <strong>MyDashboard</strong>
      <NavLink to="/">Dashboard</NavLink>
      <NavLink to="/analytics">Analytics</NavLink>
      <NavLink to="/settings">Settings</NavLink>
      <button onClick={onLogout} style={{ marginLeft: "auto" }}>Log out</button>
    </nav>
  );
}