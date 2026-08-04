export function Header({ title }: { title: string }) {
  return (
    <header style={{ background: "#ffffff", color: "#1a1a1a" }}>
      <h1>{title}</h1>
      <nav>
        <a href="/" style={{ color: "#0066cc" }}>
          Home
        </a>
        <a href="/about" style={{ color: "#0066cc" }}>
          About
        </a>
      </nav>
    </header>
  );
}
