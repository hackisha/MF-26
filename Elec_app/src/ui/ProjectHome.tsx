interface ProjectHomeProps {
  currentFileName: string | null;
  onJsonFile: (file: File) => void;
  onProjectFile: (file: File) => void;
  onExport: () => void;
}

export function ProjectHome({ currentFileName, onJsonFile, onProjectFile, onExport }: ProjectHomeProps) {
  return (
    <section className="panel">
      <h2>프로젝트 홈</h2>
      <div className="actions">
        <label className="file-action">
          EasyEDA JSON 파일
          <input
            aria-label="EasyEDA JSON 파일"
            type="file"
            accept=".json,application/json"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onJsonFile(file);
            }}
          />
        </label>
        <label className="file-action">
          프로젝트 파일
          <input
            aria-label="프로젝트 파일"
            type="file"
            accept=".json,application/json"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) onProjectFile(file);
            }}
          />
        </label>
        <button type="button" onClick={onExport}>
          프로젝트 내보내기
        </button>
      </div>
      {currentFileName ? <p className="status">최근 import: {currentFileName}</p> : null}
    </section>
  );
}
