import { useQuery } from "@tanstack/react-query";
import { fetchJobs } from "@/services/api";

export function useJobsQuery(page: number, pageSize: number) {
  return useQuery({
    queryKey: ["jobs", page, pageSize],
    queryFn: () => fetchJobs({ page, page_size: pageSize }),
    placeholderData: (previous) => previous,
  });
}
