import { useMutation } from "@tanstack/react-query";
import AuthService from "#/api/auth-service/auth-service.api";

export const useVerifyRecaptcha = () =>
  useMutation({
    mutationFn: (token: string) => AuthService.verifyRecaptcha(token),
  });
