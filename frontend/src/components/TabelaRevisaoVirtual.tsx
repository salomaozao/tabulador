import { useRef, useState, useEffect, useMemo, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { ItemResposta, Categoria } from '../types';
import { Check, Snowflake, MessageSquare } from 'lucide-react';

interface Props {
  itens: ItemResposta[];
  categorias: Categoria[];
  onConfirmar: (rid: number) => Promise<void>;
  onCorrigir: (rid: number, primaria: number, secundaria?: number | null) => Promise<void>;
  onCongelar: (rid: number, congelada: boolean) => Promise<void>;
  onComentar: (rid: number, comentario: string) => Promise<void>;
}

export const TabelaRevisaoVirtual: React.FC<Props> = ({
  itens,
  categorias,
  onConfirmar,
  onCorrigir,
  onCongelar,
  onComentar,
}) => {
  const parentRef = useRef<HTMLDivElement>(null);
  const [selectedIndex, setSelectedIndex] = useState<number>(0);
  const [filtro, setFiltro] = useState<'todos' | 'pendentes' | 'conferidos' | 'alertas' | 'discordancias'>('pendentes');
  const [busca, setBusca] = useState('');
  const [editingCommentRid, setEditingCommentRid] = useState<number | null>(null);
  const [commentText, setCommentText] = useState('');

  // Map rápido de categorias por código
  const catMap = useMemo(() => {
    const map = new Map<number, Categoria>();
    categorias.forEach((c) => map.set(c.codigo, c));
    return map;
  }, [categorias]);

  // Lista filtrada e ordenada (pendentes primeiro, conferidos no final)
  const itensFiltrados = useMemo(() => {
    return itens
      .filter((item) => {
        if (busca && !item.texto.toLowerCase().includes(busca.toLowerCase())) return false;
        if (filtro === 'pendentes') return item.status === 'pendente' || !item.humano;
        if (filtro === 'conferidos') return item.humano || item.status === 'auto';
        if (filtro === 'alertas') return Boolean(item.alertas);
        if (filtro === 'discordancias') return item.auditor_sugestao !== undefined && item.auditor_sugestao !== null && item.auditor_sugestao !== item.primaria;
        return true;
      })
      .sort((a, b) => {
        // Regra de ouro da usabilidade Olhar: Pendentes primeiro, conferidas no fim
        const aConferida = a.humano || a.status === 'auto' ? 1 : 0;
        const bConferida = b.humano || b.status === 'auto' ? 1 : 0;
        return aConferida - bConferida;
      });
  }, [itens, filtro, busca]);

  const rowVirtualizer = useVirtualizer({
    count: itensFiltrados.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 58,
    overscan: 10,
  });

  // Garantir que a linha selecionada esteja sempre visível no virtualizer
  useEffect(() => {
    if (selectedIndex >= 0 && selectedIndex < itensFiltrados.length) {
      rowVirtualizer.scrollToIndex(selectedIndex, { align: 'auto' });
    }
  }, [selectedIndex, itensFiltrados.length, rowVirtualizer]);

  // Tratamento de atalhos de teclado ágeis
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (editingCommentRid !== null) return; // não interceptar se estiver digitando comentário
      const item = itensFiltrados[selectedIndex];
      if (!item) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, itensFiltrados.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        onConfirmar(item.rid);
      } else if (e.key >= '1' && e.key <= '9') {
        const codigo = parseInt(e.key, 10);
        if (catMap.has(codigo)) {
          e.preventDefault();
          onCorrigir(item.rid, codigo, item.secundaria);
        }
      } else if (e.key.toLowerCase() === 'c') {
        e.preventDefault();
        setEditingCommentRid(item.rid);
        setCommentText(item.comentario || '');
      } else if (e.key.toLowerCase() === 's' && item.auditor_sugestao) {
        e.preventDefault();
        onCorrigir(item.rid, item.auditor_sugestao, item.secundaria);
      }
    },
    [editingCommentRid, itensFiltrados, selectedIndex, onConfirmar, onCorrigir, catMap]
  );

  return (
    <div className="tabela-virtual-container" onKeyDown={handleKeyDown} tabIndex={0} style={{ outline: 'none' }}>
      {/* Barra de Filtros e Ferramentas */}
      <div className="tools" style={{ justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {(['pendentes', 'todos', 'conferidos', 'alertas', 'discordancias'] as const).map((f) => (
            <button
              key={f}
              className={`btn sm ${filtro === f ? 'primary' : 'ghost'}`}
              onClick={() => {
                setFiltro(f);
                setSelectedIndex(0);
              }}
            >
              {f === 'pendentes' && '⏳ Pendentes'}
              {f === 'todos' && 'Todas'}
              {f === 'conferidos' && '✓ Conferidas'}
              {f === 'alertas' && '⚠️ Alertas'}
              {f === 'discordancias' && '🔎 Discordâncias'}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="search"
            placeholder="Buscar nas respostas..."
            value={busca}
            onChange={(e) => {
              setBusca(e.target.value);
              setSelectedIndex(0);
            }}
            style={{ width: '220px', fontSize: '12px' }}
          />
          <span className="small muted">
            {itensFiltrados.length} de {itens.length} respostas
          </span>
        </div>
      </div>

      {/* Cabeçalho da Tabela */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '80px 1fr 220px 180px 90px',
          padding: '8px 12px',
          background: 'var(--surface-2)',
          fontWeight: 600,
          fontSize: '12px',
          color: 'var(--text-2)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div>Qtd (N)</div>
        <div>Resposta (Verbatim)</div>
        <div>Categoria Principal</div>
        <div>Secundária / Auditor</div>
        <div style={{ textAlign: 'right' }}>Ações</div>
      </div>

      {/* Área Virtualizada */}
      <div
        ref={parentRef}
        style={{
          height: '620px',
          overflowY: 'auto',
          position: 'relative',
          background: 'var(--surface)',
        }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const item = itensFiltrados[virtualRow.index];
            const isSelected = selectedIndex === virtualRow.index;
            const isConferida = item.humano || item.status === 'auto';
            const catSecundaria = item.secundaria ? catMap.get(item.secundaria) : null;
            const auditorCat = item.auditor_sugestao ? catMap.get(item.auditor_sugestao) : null;

            return (
              <div
                key={item.rid}
                onClick={() => setSelectedIndex(virtualRow.index)}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                  display: 'grid',
                  gridTemplateColumns: '80px 1fr 220px 180px 90px',
                  alignItems: 'center',
                  padding: '6px 12px',
                  fontSize: '13px',
                  borderBottom: '1px solid var(--border)',
                  background: isSelected
                    ? 'var(--surface-3)'
                    : isConferida
                    ? 'color-mix(in srgb, var(--ok-bg) 30%, transparent)'
                    : 'transparent',
                  boxShadow: isSelected ? 'inset 3px 0 0 var(--accent)' : 'none',
                  cursor: 'pointer',
                }}
              >
                {/* N */}
                <div style={{ fontVariantNumeric: 'tabular-nums', fontWeight: 600, color: 'var(--text-2)' }}>
                  {item.n}x
                  {item.congelada && (
                    <Snowflake size={12} color="var(--accent)" style={{ marginLeft: '4px', verticalAlign: 'middle' }} />
                  )}
                </div>

                {/* Texto da Resposta */}
                <div style={{ paddingRight: '12px', overflow: 'hidden' }}>
                  <div
                    style={{
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      color: isConferida ? 'var(--text-2)' : 'var(--text)',
                    }}
                    title={item.texto}
                  >
                    {item.texto}
                  </div>
                  {item.comentario && (
                    <div className="small" style={{ color: 'var(--warn)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MessageSquare size={10} /> {item.comentario}
                    </div>
                  )}
                </div>

                {/* Categoria Principal */}
                <div>
                  <select
                    className="cat"
                    value={item.primaria ?? ''}
                    onChange={(e) => {
                      const val = e.target.value ? parseInt(e.target.value, 10) : null;
                      if (val) onCorrigir(item.rid, val, item.secundaria);
                    }}
                    style={{ fontSize: '12px', padding: '3px 6px' }}
                  >
                    <option value="">(Sem categoria)</option>
                    {categorias.map((c) => (
                      <option key={c.codigo} value={c.codigo}>
                        {c.codigo}. {c.nome}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Secundária ou Sugestão do Auditor */}
                <div style={{ fontSize: '11px', color: 'var(--text-2)' }}>
                  {item.auditor_sugestao && item.auditor_sugestao !== item.primaria ? (
                    <span
                      className="pill warn"
                      title="Clique para aceitar a sugestão da 2ª IA"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (item.auditor_sugestao) onCorrigir(item.rid, item.auditor_sugestao, item.secundaria);
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      Auditor: {auditorCat?.nome || item.auditor_sugestao}
                    </span>
                  ) : catSecundaria ? (
                    <span className="pill">{catSecundaria.nome}</span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </div>

                {/* Ações */}
                <div style={{ textAlign: 'right', display: 'flex', gap: '4px', justifyContent: 'flex-end' }}>
                  <button
                    className={`btn sm ${item.congelada ? 'primary' : 'ghost'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCongelar(item.rid, !item.congelada);
                    }}
                    title={item.congelada ? 'Descongelar resposta' : 'Congelar resposta (protege contra IA)'}
                    style={{ padding: '2px 6px' }}
                  >
                    <Snowflake size={13} color={item.congelada ? '#fff' : 'var(--text-3)'} />
                  </button>
                  <button
                    className={`btn sm ${isConferida ? 'ok' : 'primary'}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onConfirmar(item.rid);
                    }}
                    title="Confirmar (Enter)"
                    style={{ padding: '2px 8px' }}
                  >
                    <Check size={13} />
                  </button>
                  <button
                    className="btn sm ghost"
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingCommentRid(item.rid);
                      setCommentText(item.comentario || '');
                    }}
                    title="Comentar (C)"
                    style={{ padding: '2px 6px' }}
                  >
                    <MessageSquare size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Barra de Ajuda / Atalhos Rápidos */}
      <div
        style={{
          display: 'flex',
          gap: '16px',
          padding: '6px 12px',
          background: 'var(--surface-2)',
          borderTop: '1px solid var(--border)',
          fontSize: '11px',
          color: 'var(--text-3)',
        }}
      >
        <span><kbd>↑</kbd><kbd>↓</kbd> Navegar</span>
        <span><kbd>Enter</kbd> Confirmar ✓</span>
        <span><kbd>1</kbd>–<kbd>9</kbd> Trocar Categoria</span>
        <span><kbd>C</kbd> Comentário</span>
        <span><kbd>S</kbd> Aceitar Auditor</span>
      </div>

      {/* Modal / Diálogo de Comentário */}
      {editingCommentRid !== null && (
        <div className="busy" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="box" style={{ width: '420px', flexDirection: 'column', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '14px' }}>Comentário / Instrução para esta resposta</h3>
            <textarea
              autoFocus
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="Ex: Não pertence a X, colocar em Y..."
              rows={4}
              style={{ width: '100%', fontSize: '13px' }}
            />
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', width: '100%' }}>
              <button className="btn sm ghost" onClick={() => setEditingCommentRid(null)}>
                Cancelar (Esc)
              </button>
              <button
                className="btn sm primary"
                onClick={() => {
                  onComentar(editingCommentRid, commentText);
                  setEditingCommentRid(null);
                }}
              >
                Salvar Comentário
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
