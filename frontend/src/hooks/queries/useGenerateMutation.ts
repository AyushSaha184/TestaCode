import { useMutation, useQueryClient } from "@tanstack/react-query";
import { generateTests } from "@/services/api";

export function useGenerateMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: generateTests,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
