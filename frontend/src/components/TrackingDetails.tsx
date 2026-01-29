import React, { useState, useEffect } from 'react';
import {
  FiPackage, FiTruck, FiCalendar, FiUser, FiFileText, FiLayers,
  FiCheckCircle, FiAlertCircle, FiClock, FiHash, FiChevronDown
} from 'react-icons/fi';
import type { DatabaseRow } from '../types/bi.types';

interface TrackingDetailsProps {
  data: DatabaseRow[];
  title?: string;
}

// Subcomponente Custom Dropdown
const CustomDropdown = ({ data, selected, onSelect }: { data: DatabaseRow[], selected: string | number, onSelect: (val: string | number) => void }) => {
  const [isOpen, setIsOpen] = useState(false);

  // Fecha ao clicar fora (simples implementação)
  useEffect(() => {
    const close = () => setIsOpen(false);
    if (isOpen) window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, [isOpen]);

  const handleSelect = (val: string | number, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(val);
    setIsOpen(false);
  };

  const toggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
  };

  const selectedItem = data.find((item, idx) => {
    const rawValue = item['SERIE'] !== undefined && item['SERIE'] !== null ? item['SERIE'] : idx;
    return String(rawValue) === String(selected);
  });

  const rawSerie = selectedItem ? selectedItem['SERIE'] : '';
  const displayLabel = (rawSerie && String(rawSerie) !== '0') ? `SÉRIE ${rawSerie}` : `ITEM ${data.findIndex(i => i === selectedItem) + 1}`;

  return (
    <div className="tracking-custom-dropdown">
      <div className="tracking-dropdown-trigger" onClick={toggle}>
        {displayLabel}
        <FiChevronDown className={`tracking-dropdown-arrow ${isOpen ? 'open' : ''}`} />
      </div>
      {isOpen && (
        <div className="tracking-dropdown-menu">
          {data.map((item, idx) => {
            const rSerie = item['SERIE'];
            const label = (rSerie && String(rSerie) !== '0') ? `SÉRIE ${rSerie}` : `ITEM ${idx + 1}`;
            const val = rSerie !== undefined && rSerie !== null ? rSerie : idx;
            const safeVal = (typeof val === 'boolean') ? String(val) : val;
            const isSelected = String(safeVal) === String(selected);

            return (
              <div
                key={idx}
                className={`tracking-dropdown-item ${isSelected ? 'selected' : ''}`}
                onClick={(e) => handleSelect(safeVal, e)}
              >
                {label}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export const TrackingDetails: React.FC<TrackingDetailsProps> = ({ data, title = "Rastreamento" }) => {
  if (!data || !Array.isArray(data) || data.length === 0) return null;

  const [selectedSerie, setSelectedSerie] = useState<string | number>('');

  useEffect(() => {
    if (data.length > 0) {
      const firstItem = data[0];
      const initialSerie = firstItem['SERIE'] !== undefined && firstItem['SERIE'] !== null
        ? firstItem['SERIE']
        : (data.length > 1 ? 0 : 'Única');
      setSelectedSerie(initialSerie as string | number);
    }
  }, [data]);

  const activeRecord = data.find((item, idx) => {
    const itemSerie = item['SERIE'] !== undefined && item['SERIE'] !== null
      ? item['SERIE']
      : idx;
    return String(itemSerie) === String(selectedSerie);
  }) || data[0];

  const formatLabel = (key: string) => {
    const map: Record<string, string> = {
      'NOTA_FISCAL': 'Nota Fiscal',
      'STA_NOTA': 'Status',
      'DESTINATARIO': 'Cliente',
      'EMISSAO': 'Emissão',
      'TRANPORTADORA': 'Transportadora',
      'SERIE': 'Série',
      'DDESTINATARIO': 'Cliente',
      'VLR_TOTAL': 'Valor',
      'PESO_BRUTO': 'Peso'
    };
    return map[key] || key.replace(/_/g, ' ').toLowerCase();
  };

  // NOVA FUNÇÃO: Formata valores (Datas, Moeda, etc)
  const formatValue = (key: string, value: any) => {
    if (value === null || value === undefined) return '-';

    const strVal = String(value);
    const upperKey = key.toUpperCase();

    // Formatação de DATA (ISO para PT-BR)
    if (upperKey.includes('EMISSAO') || upperKey.includes('DATA')) {
      try {
        // Tenta criar data. Se for string ISO válida, formata.
        const date = new Date(strVal);
        if (!isNaN(date.getTime())) {
          return new Intl.DateTimeFormat('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          }).format(date);
        }
      } catch (e) {
        return strVal; // Se falhar, retorna original
      }
    }

    return strVal;
  };

  const getIcon = (key: string) => {
    const k = key.toUpperCase();
    if (k.includes('STA')) return <FiCheckCircle />;
    if (k.includes('TRANS')) return <FiTruck />;
    if (k.includes('EMISSAO') || k.includes('DATA')) return <FiCalendar />;
    if (k.includes('DEST') || k.includes('CLI')) return <FiUser />;
    if (k.includes('SERIE')) return <FiLayers />;
    if (k.includes('NOTA')) return <FiHash />;
    return <FiFileText />;
  };

  const getStatusClass = (status: string) => {
    const s = status.toUpperCase();
    if (s.includes('BLOQUEADO') || s.includes('CANCELADO')) return 'status-error';
    if (s.includes('EXPEDIDO') || s.includes('ENTREGUE')) return 'status-success';
    if (s.includes('SEPARA') || s.includes('ONDA')) return 'status-warning';
    return 'status-info';
  };

  const ignoredKeys = ['last_updated', 'id', 'uuid', 'pk'];

  // ALTERAÇÃO: Adicionado 'SERIE' aqui para não repetir na lista, já que está no header
  const highlightedKeys = ['NOTA_FISCAL', 'STA_NOTA', 'SERIE'];

  const displayKeys = Object.keys(activeRecord).filter(k =>
    !ignoredKeys.includes(k) && !highlightedKeys.includes(k)
  );

  const currentStatus = String(activeRecord['STA_NOTA'] || 'DESCONHECIDO');
  const displaySerie = (activeRecord['SERIE'] !== undefined && activeRecord['SERIE'] !== null && String(activeRecord['SERIE']) !== '0')
    ? activeRecord['SERIE']
    : 'N/A';

  return (
    <div className="tracking-card">

      {/* 1. CABEÇALHO REESTRUTURADO */}
      <div className="tracking-header-wrapper">
        {/* Título Principal Fora do Flex do Header */}
        <span className="tracking-main-title">{title}</span>

        <div className="tracking-header">
          <div className="tracking-header-main">
            <div className="tracking-big-number">
              {/* Verifica se tem NOTA_FISCAL para exibir label "NOTA:" antes */}
              {activeRecord['NOTA_FISCAL'] ? (
                <>
                  <span className="tracking-number-label">NOTA:</span>
                  {String(activeRecord['NOTA_FISCAL'])}
                </>
              ) : (
                '---'
              )}
            </div>
          </div>

          {/* LADO DIREITO: Custom Dropdown ou Badge */}
          {data.length > 1 ? (
            <CustomDropdown
              data={data}
              selected={selectedSerie}
              onSelect={setSelectedSerie}
            />
          ) : (
            <div className="tracking-badge-serie">
              <span>SÉRIE</span>
              <strong>{String(displaySerie)}</strong>
            </div>
          )}
        </div>
      </div>

      {/* 4. RODAPÉ FIXO (Mantido, mas o wrapper de abas foi removido acima) */}

      {/* 3. LISTA VERTICAL */}
      <div className="tracking-list-container">
        {displayKeys.map((key) => (
          <div key={key} className="tracking-list-row">
            <div className="tracking-item-label">
              <span className="tracking-icon-wrapper">{getIcon(key)}</span>
              {formatLabel(key)}
            </div>
            {/* ALTERAÇÃO: Usando formatValue aqui e estilizando STATUS */}
            <div className="tracking-item-value" title={String(activeRecord[key])}>
              {key === 'STA_NOTA' ? (
                <span className="tracking-value-status">{formatValue(key, activeRecord[key])}</span>
              ) : (
                formatValue(key, activeRecord[key])
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 4. RODAPÉ FIXO */}
      <div className={`tracking-footer ${getStatusClass(currentStatus)}`}>
        <span className="status-dot"></span>
        {currentStatus}
      </div>
    </div>
  );
};