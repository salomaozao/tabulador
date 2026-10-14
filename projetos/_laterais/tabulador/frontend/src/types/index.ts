export interface Categoria {
  codigo: number;
  nome: string;
  definicao?: string;
  exemplos?: string[];
  keywords?: string[];
  origem?: string;
}

export interface Frame {
  status: 'rascunho' | 'aprovado' | string;
  categorias: Categoria[];
  aprovado_em?: string;
  aprovado_por?: string;
  modificado_apos_aprovacao?: boolean;
}

export interface ItemResposta {
  rid: number;
  texto: string;
  n: number;
  primaria: number | null;
  secundaria: number | null;
  status?: 'confirmado' | 'corrigido' | 'auto' | 'pendente' | string;
  humano?: boolean;
  alertas?: string | null;
  comentario?: string | null;
  comentario_pendente?: boolean;
  congelada?: boolean;
  confianca?: number;
  auditor_sugestao?: number | null;
  auditor_modelo?: string | null;
  _q?: string; // Questão de origem se grupo
}

export interface PerguntaPayload {
  qid: string;
  rotulo?: string;
  backcoding?: boolean;
  instrucoes_fixas?: string;
  instrucoes?: string;
  frame?: Frame | null;
  itens: ItemResposta[];
  contagens: Record<string, { primaria: number; secundaria: number }>;
  n_alertas: number;
  n_comentarios_pendentes: number;
  revisao?: {
    total: number;
    conferidas: number;
    confirmadas: number;
    corrigidas: number;
    acerto_ia: number;
    auto_aceitas?: number;
  } | null;
  conferencia?: any;
  saude?: any[];
  grupo?: any;
}

export interface StatusProjeto {
  projeto_ativo: string;
  projetos: Record<string, { nome: string; pasta: string }>;
  perguntas: Array<{
    id: string;
    rotulo: string;
    total: number;
    classificadas: number;
    status: 'pendente' | 'em_andamento' | 'aprovado';
    frame_status: string;
    acerto_ia?: number;
    grupo?: string;
  }>;
  base: {
    carregada: boolean;
    n: number;
    fonte: string;
  };
  nuvem?: {
    ativa: boolean;
    conectada: boolean;
  };
}
