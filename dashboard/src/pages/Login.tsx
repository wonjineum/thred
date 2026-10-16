type Props = { onLogin: () => void };

export default function Login({ onLogin }: Props) {
  return (
    <div style={{ maxWidth: 320, margin: "100px auto", display: "grid", gap: 12 }}>
      <h2>Log in</h2>
      <input type="email" placeholder="Email" />
      <input type="password" placeholder="Password" />
      <button onClick={onLogin}>Log in</button>
    </div>
  );
}