import { useNavigate } from "react-router-dom";

type Props = { onSignup: () => void };

export default function Signup({ onSignup }: Props) {
  const navigate = useNavigate();

  return (
    <div style={{ maxWidth: 320, margin: "100px auto", display: "grid", gap: 12 }}>
      <h2>Create account</h2>
      <input type="text" placeholder="Name" />
      <input type="email" placeholder="Email" />
      <input type="password" placeholder="Password" />
      <input type="password" placeholder="Confirm password" />
      <button onClick={onSignup}>Sign up</button>
      <button onClick={() => navigate("/login")}>Already have an account? Log in</button>
    </div>
  );
}