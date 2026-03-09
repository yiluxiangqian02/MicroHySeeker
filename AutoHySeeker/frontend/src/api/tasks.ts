import { apiClient } from "@/api/client";
import type { TaskCreateRequest, TaskRecord } from "@/api/types";

export const tasksApi = {
  async create(payload: TaskCreateRequest): Promise<TaskRecord> {
    const response = await apiClient.post<TaskRecord>("/tasks/create", payload);
    return response.data;
  },

  async getStatus(taskId: string): Promise<TaskRecord> {
    const response = await apiClient.get<TaskRecord>(`/tasks/${taskId}/status`);
    return response.data;
  }
};

