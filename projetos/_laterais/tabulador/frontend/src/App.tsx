import { useState, useEffect, useCallback } from 'react';
import './app.css';
import { api, getUsuario, setUsuario } from './api/client';
import type { StatusProjeto, PerguntaPayload } from './types';
import { TabelaRevisaoVirtual } from './components/TabelaRevisaoVirtual';
import { 
  Cloud, 
  CheckCircle, 
  Play, 
  Zap, 
  Folder, 
  User
} from 'lucide-react';

export default function App() {
  const [status, setStatus] = useState<StatusProjeto | null>(null);
  const [selectedQid, setSelectedQid] = useState<string | null>(null);
  const [pergunta, setPergunta] = useState<PerguntaPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyMessage, setBusyMessage] = useState<string | null>(null);
  const [userName, setUserName] = useState(getUsuario());

  // Carregar status inicial
  const carregarStatus = useCallback(async () => {
    try {
      const data = await api.getStatus();
      setStatus(data);
      if (!selectedQid && data.perguntas.length > 0) {
        setSelectedQid(data.perguntas[0].id);
      }
    } catch (err: any) {
      console.error('Falha ao carregar status:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedQid]);

  useEffect(() => {
    carregarStatus();
  }, [carregarStatus]);

  // Carregar dados da pergunta selecionada
  const carregarPergunta = useCallback(async (qid: string) => {
    try {
      setLoading(true);
      const data = await api.getPergunta(qid);
      setPergunta(data);
    } catch (err: any) {
      console.error('Falha ao carregar pergunta:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedQid) {
      carregarPergunta(selectedQid);
    }
  }, [selectedQid, carregarPergunta]);

  // Ações otimistas de revisão (0ms latência)
  const handleConfirmar = async (rid: number) => {
    if (!pergunta || !selectedQid) return;

    // Optimistic Update: atualiza imediatamente o estado local
    setPergunta((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        itens: prev.itens.map((item) => {
          if (item.rid === rid) {
            return { ...item, humano: true, status: 'confirmado' };
          }
          return item;
        }),
      };
    });

    try {
      const item = pergunta.itens.find((i) => i.rid === rid);
      await api.atualizarItem(selectedQid, rid, {
        primaria: item?.primaria ?? null,
        secundaria: item?.secundaria ?? null,
        comentario: item?.comentario ?? undefined,
        acao: 'confirmar',
      });
    } catch (err: any) {
      alert(`Erro ao confirmar: ${err.message}`);
      carregarPergunta(selectedQid); // rollback
    }
  };

  const handleCorrigir = async (rid: number, primaria: number, secundaria?: number | null) => {
    if (!pergunta || !selectedQid) return;

    setPergunta((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        itens: prev.itens.map((item) => {
          if (item.rid === rid) {
            return { ...item, primaria, secundaria: secundaria ?? item.secundaria, humano: true, status: 'corrigido' };
          }
          return item;
        }),
      };
    });

    try {
      await api.atualizarItem(selectedQid, rid, {
        primaria,
        secundaria,
        acao: 'corrigir',
      });
    } catch (err: any) {
      alert(`Erro ao corrigir: ${err.message}`);
      carregarPergunta(selectedQid);
    }
  };

  const handleCongelar = async (rid: number, congelada: boolean) => {
    if (!pergunta || !selectedQid) return;
    setPergunta((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        itens: prev.itens.map((item) => (item.rid === rid ? { ...item, congelada } : item)),
      };
    });
    try {
      await api.congelarItem(selectedQid, rid, congelada);
    } catch (err: any) {
      alert(`Erro ao congelar: ${err.message}`);
      carregarPergunta(selectedQid);
    }
  };

  const handleComentar = async (rid: number, comentario: string) => {
    if (!pergunta || !selectedQid) return;
    setPergunta((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        itens: prev.itens.map((item) => (item.rid === rid ? { ...item, comentario } : item)),
      };
    });
    try {
      const item = pergunta.itens.find((i) => i.rid === rid);
      await api.atualizarItem(selectedQid, rid, {
        primaria: item?.primaria ?? null,
        secundaria: item?.secundaria ?? null,
        comentario,
        acao: 'corrigir',
      });
    } catch (err: any) {
      alert(`Erro ao comentar: ${err.message}`);
      carregarPergunta(selectedQid);
    }
  };

  const handleClassificarAmostra = async (n = 50) => {
    if (!selectedQid) return;
    setBusyMessage(`Classificando amostra de ${n} respostas com IA...`);
    try {
      await api.codificar(selectedQid, { n });
      await carregarPergunta(selectedQid);
      await carregarStatus();
    } catch (err: any) {
      alert(`Erro na classificação: ${err.message}`);
    } finally {
      setBusyMessage(null);
    }
  };

  const handleAutoAceitar = async () => {
    if (!selectedQid) return;
    setBusyMessage('Aceitando automaticamente casos de alta confiança...');
    try {
      await api.autoAceitar(selectedQid, 0.85);
      await carregarPergunta(selectedQid);
      await carregarStatus();
    } catch (err: any) {
      alert(`Erro no auto-aceite: ${err.message}`);
    } finally {
      setBusyMessage(null);
    }
  };

  return (
    <div className="tabulador-app">
      {/* Topo Global */}
      <header className="top">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Folder size={18} color="var(--accent)" />
          <span>Tabulador de Respostas Abertas</span>
          {status && (
            <select
              value={status.projeto_ativo}
              onChange={(e) => api.trocarProjeto(e.target.value).then(() => window.location.reload())}
              style={{ marginLeft: '12px', fontSize: '13px', padding: '3px 8px' }}
            >
              {Object.entries(status.projetos).map(([id, p]) => (
                <option key={id} value={id}>
                  {p.nome}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Status da Nuvem Turso */}
        <div className="nuvem-status" title="Banco distribuído Turso">
          <Cloud size={14} color="var(--ok)" />
          <span className="dot ok"></span>
          <span>Nuvem Turso</span>
        </div>

        {/* Identificação do Usuário */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
          <User size={14} color="var(--text-2)" />
          <input
            className="inline"
            value={userName}
            onChange={(e) => {
              setUserName(e.target.value);
              setUsuario(e.target.value);
            }}
            title="Seu nome para a lista de presença e auditoria"
            style={{ width: '110px', fontSize: '12px' }}
          />
        </div>
      </header>

      {/* Grid Principal */}
      <div className="layout">
        {/* Barra Lateral com Perguntas */}
        <aside className="side">
          <div className="side-title">Perguntas da Pesquisa</div>
          <ul>
            {status?.perguntas.map((p) => {
              const isAtiva = selectedQid === p.id;
              const isAprovada = p.status === 'aprovado';
              return (
                <li
                  key={p.id}
                  className={isAtiva ? 'ativa' : ''}
                  onClick={() => setSelectedQid(p.id)}
                >
                  <div className="t">
                    <span style={{ fontWeight: 600 }}>{p.id}</span>
                    {isAprovada && <CheckCircle size={13} color="var(--ok)" />}
                  </div>
                  <div className="small muted" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {p.rotulo || p.id}
                  </div>
                  <div className="meta-base" style={{ fontSize: '11px', gap: '8px' }}>
                    <span>{p.classificadas}/{p.total} classif.</span>
                    {p.acerto_ia !== undefined && (
                      <span style={{ color: p.acerto_ia >= 0.85 ? 'var(--ok)' : 'var(--warn)' }}>
                        {Math.round(p.acerto_ia * 100)}% acerto
                      </span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* Conteúdo Principal */}
        <main>
          {loading && !pergunta ? (
            <div className="empty">Carregando dados da pesquisa...</div>
          ) : pergunta ? (
            <div>
              {/* Cabeçalho da Pergunta */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <h1 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>{pergunta.qid}</span>
                    {pergunta.frame?.status === 'aprovado' && <span className="pill ok">✓ Quadro Aprovado</span>}
                  </h1>
                  <p className="muted" style={{ margin: '4px 0 0', fontSize: '14px' }}>
                    {pergunta.rotulo}
                  </p>
                </div>

                {/* Ações de IA Rápidas */}
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn sm primary" onClick={() => handleClassificarAmostra(50)} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Play size={13} /> Classificar 50
                  </button>
                  <button className="btn sm ghost" onClick={() => handleClassificarAmostra(200)}>
                    +200
                  </button>
                  <button className="btn sm ghost" onClick={handleAutoAceitar} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Zap size={13} color="var(--warn)" /> Auto-Aceitar (≥85%)
                  </button>
                  <button className="btn sm ok" onClick={() => api.aprovarPergunta(pergunta.qid).then(() => carregarPergunta(pergunta.qid))}>
                    ✓ Aprovar Pergunta
                  </button>
                </div>
              </div>

              {/* Indicadores / Tiles */}
              <div className="tiles">
                <div className="tile">
                  <div className="l">Total de Respostas</div>
                  <div className="v">{pergunta.itens.length}</div>
                </div>
                <div className="tile">
                  <div className="l">Classificadas</div>
                  <div className="v">{pergunta.revisao?.total || 0}</div>
                </div>
                <div className="tile">
                  <div className="l">Conferidas por Humanos</div>
                  <div className="v">{pergunta.revisao?.conferidas || 0}</div>
                </div>
                <div className="tile">
                  <div className="l">Taxa de Acerto da IA</div>
                  <div className="v" style={{ color: (pergunta.revisao?.acerto_ia || 0) >= 0.85 ? 'var(--ok)' : 'var(--warn)' }}>
                    {pergunta.revisao ? `${Math.round(pergunta.revisao.acerto_ia * 100)}%` : '—'}
                  </div>
                </div>
              </div>

              {/* Tabela de Revisão Virtualizada (60 FPS) */}
              <div style={{ marginTop: '20px' }}>
                <h2 style={{ margin: '0 0 10px', fontSize: '14px', fontWeight: 600 }}>
                  Triagem & Conferência de Respostas
                </h2>
                <TabelaRevisaoVirtual
                  itens={pergunta.itens}
                  categorias={pergunta.frame?.categorias || []}
                  onConfirmar={handleConfirmar}
                  onCorrigir={handleCorrigir}
                  onCongelar={handleCongelar}
                  onComentar={handleComentar}
                />
              </div>
            </div>
          ) : (
            <div className="empty">Selecione uma pergunta na barra lateral para começar.</div>
          )}
        </main>
      </div>

      {/* Modal de Operação em Andamento */}
      {busyMessage && (
        <div className="busy">
          <div className="box">
            <div className="cat-spin"></div>
            <div className="busy-info">
              <b>Processando com IA</b>
              <div className="small muted">{busyMessage}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
