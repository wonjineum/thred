import { useNavigate } from "react-router-dom";

export default function Intro() {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: 400, margin: "100px auto", textAlign: "center", display: "grid", gap: 12 }}>
      <h1>Welcome to Thred</h1>
      <p>See your purchases</p>
      <button onClick={() => navigate("/signup")}>Get started</button>
      <button onClick={() => navigate("/login")}>I already have an account</button>
    </div>
  );
}