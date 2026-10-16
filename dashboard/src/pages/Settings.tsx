export default function Settings() {
  return (
    <div style={{ maxWidth: 400, display: "grid", gap: 12 }}>
      <h1>Settings</h1>
      <input type="text" placeholder="Name" />
      <input type="email" placeholder="Email" />
      <input type="password" placeholder="New password" />
      <button>Save changes</button>
    </div>
  );
}