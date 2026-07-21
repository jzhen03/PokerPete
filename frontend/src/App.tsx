import { useQuery } from "@tanstack/react-query";
import { apiGet } from "./api/client";

interface HealthResponse {
  status: string;
}

function App() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet<HealthResponse>("/health"),
  });

  return (
    <main>
      <h1>PokerPete</h1>
      <p>
        Backend status:{" "}
        {isLoading ? "checking..." : isError ? "unreachable" : data?.status}
      </p>
    </main>
  );
}

export default App;
