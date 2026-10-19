import type { PerguntaPayload, StatusProjeto } from '../types';

let currentUser = localStorage.getItem('tabulador_usuario') || 'Pesquisador';

export function setUsuario(nome: string) {
  currentUser = nome;
  localStorage.setItem('tabulador_usuario', nome);
}

export function getUsuario(): string {
  return currentUser;
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = {
    'Content-Type': 'application/json',
    'X-Tabulador-Usuario': encodeURIComponent(currentUser),
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let msg = `Erro ${response.status}: ${response.statusText}`;
    try {
      const data = await response.json();
      if (data.erro) msg = data.erro;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return response.json();
}

export const api = {
  getStatus: () => request<StatusProjeto>('/api/status'),
  
  getPergunta: (qid: string) => request<PerguntaPayload>(`/api/pergunta/${encodeURIComponent(qid)}`),
  
  atualizarItem: (
    qid: string,
    rid: number,
    payload: {
      primaria: number | null;
      secundaria?: number | null;
      comentario?: string;
      acao: 'confirmar' | 'corrigir';
    }
  ) => request(`/api/pergunta/${encodeURIComponent(qid)}/item/${rid}`, {
    method: 'POST',
    body: JSON.stringify(payload),
  }),

  congelarItem: (qid: string, rid: number, congelada: boolean) =>
    request(`/api/pergunta/${encodeURIComponent(qid)}/item/${rid}/congelar`, {
      method: 'POST',
      body: JSON.stringify({ congelada }),
    }),

  codificar: (qid: string, params: { n?: number; modelo?: string; todas?: boolean }) =>
    request(`/api/pergunta/${encodeURIComponent(qid)}/codificar`, {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  autoAceitar: (qid: string, limiar = 0.85) =>
    request(`/api/pergunta/${encodeURIComponent(qid)}/auto-aceitar`, {
      method: 'POST',
      body: JSON.stringify({ limiar }),
    }),

  auditar: (qid: string, modelo?: string) =>
    request(`/api/pergunta/${encodeURIComponent(qid)}/auditar`, {
      method: 'POST',
      body: JSON.stringify({ modelo }),
    }),

  aprovarPergunta: (qid: string) =>
    request(`/api/pergunta/${encodeURIComponent(qid)}/aprovar`, {
      method: 'POST',
    }),

  trocarProjeto: (nome: string) =>
    request('/api/projeto', {
      method: 'POST',
      body: JSON.stringify({ projeto: nome }),
    }),
};
