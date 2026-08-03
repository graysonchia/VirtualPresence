import type {
  EnrollmentResponse,
  IdentificationResponse,
  UserListResponse,
} from "../types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  return new ApiError(
    body?.detail ?? `Request failed with status ${response.status}.`,
    response.status,
  );
}

export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response.json() as Promise<T>;
}

export async function requestVoid(
  path: string,
  options?: RequestInit,
): Promise<void> {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
}

export async function requestBlob(
  path: string,
  options?: RequestInit,
): Promise<Blob> {
  const response = await fetch(`${API_URL}${path}`, options);
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response.blob();
}

export async function enrollFace(input: {
  image: Blob;
  name: string;
  email?: string;
  preferredLanguage: string;
}): Promise<EnrollmentResponse> {
  const form = new FormData();
  form.append("image", input.image, "webcam-capture.jpg");
  form.append("name", input.name);
  if (input.email) form.append("email", input.email);
  form.append("preferred_language", input.preferredLanguage);
  return request<EnrollmentResponse>("/face/enroll", {
    method: "POST",
    body: form,
  });
}

export async function identifyFace(input: {
  image: Blob;
  frames: Blob[];
}): Promise<IdentificationResponse> {
  const form = new FormData();
  form.append("image", input.image, "webcam-capture.jpg");
  input.frames.forEach((frame, index) => {
    form.append("frames", frame, `liveness-frame-${index + 1}.jpg`);
  });
  return request<IdentificationResponse>("/face/identify", {
    method: "POST",
    body: form,
  });
}

export function getUsers(): Promise<UserListResponse> {
  return request<UserListResponse>("/face/users");
}
