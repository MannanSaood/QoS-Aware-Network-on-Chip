function plot_primary_results(resultDir,exportIndividuals,onlyMeshes)
% Full measured load sweeps, individual figures and six-traffic comparison pages.
if nargin<1, resultDir=fullfile('results','primary_report'); end
if nargin<2, exportIndividuals=true; end
if nargin<3, onlyMeshes=[]; end
P=jsondecode(fileread(fullfile(resultDir,'figure_data.json')));
G=jsondecode(fileread(fullfile(resultDir,'slide_data.json')));
V=jsondecode(fileread(fullfile(resultDir,'validation.json')));
warmup=1000; measured=3000;
if isfield(V,'warmup_cycles'), warmup=V.warmup_cycles; measured=V.measurement_cycles; end
out=fullfile(resultDir,'matlab_figures'); grouped=fullfile(resultDir,'comparison_pages');
if ~isfolder(out), mkdir(out); end
if ~isfolder(grouped), mkdir(grouped); end
T=readtable(fullfile(resultDir,'measured_runs.csv'),'TextType','string');
C=table; CS=table;
if isfile(fullfile(resultDir,'per_class_runs.csv'))
    C=readtable(fullfile(resultDir,'per_class_runs.csv'),'TextType','string');
    CS=readtable(fullfile(resultDir,'per_class_summary.csv'),'TextType','string');
end
save(fullfile(resultDir,'simulation_data.mat'),'T','C','CS','P','G','V');
if exportIndividuals
for i=1:numel(P)
    p=P(i);
    if ~isempty(onlyMeshes) && ~ismember(p.mesh_k,onlyMeshes), continue; end
    fprintf('Rendering %dx%d %s: %s\n',p.mesh_k,p.mesh_k,p.traffic,p.metric);
    f=baseFigure([23 16]);
    ax=axes(f,'Position',[.14 .25 .82 .55]);
    drawPanel(ax,p,true);
    title(ax,sprintf('%dx%d mesh: %s',p.mesh_k,p.mesh_k,p.title),'FontSize',15,'Color',[.1 .1 .1]);
    xlabel(ax,'Offered injection (% of one flit/node/cycle)'); ylabel(ax,p.ylabel);
    legend(ax,'Location','best','Box','off','Color','w','TextColor',[.1 .1 .1]);
    notes={'Lines: three-seed means. Bands: 95% t-intervals.', ...
         sprintf('%s warm-up + %s measured cycles. Latency excludes unfinished packets.',num2str(warmup),num2str(measured))};
    if isfield(V,'caption'), notes=[{char(V.caption)},notes]; end
    annotation(f,'textbox',[.14 .025 .82 .14],'String',notes, ...
        'EdgeColor','none','FontName','Arial','FontSize',9,'Color',[.3 .3 .3]);
    stem=sprintf('k%d_%s_%s',p.mesh_k,p.traffic,p.metric);
    saveExports(f,out,stem); close(f);
    if mod(i,6)==0, fprintf('Exported %d/%d individual figures\n',i,numel(P)); end
end
end
for i=1:numel(G)
    g=G(i);
    if ~isempty(onlyMeshes) && ~ismember(g.mesh_k,onlyMeshes), continue; end
    f=baseFigure([40 24]);
    tiles=tiledlayout(f,2,3,'TileSpacing','compact','Padding','compact');
    for pi=1:6
        ax=nexttile(tiles); drawPanel(ax,g.panels(pi),false);
        title(ax,g.panels(pi).title,'FontSize',14,'FontWeight','bold','Color',[.1 .1 .1]);
        if pi>3, xlabel(ax,'Offered injection (%)'); end
        if mod(pi,3)==1, ylabel(ax,g.panels(pi).ylabel); end
    end
    lg=legend(ax,'Orientation','horizontal','Box','off','Color','w','TextColor',[.1 .1 .1],'FontSize',13);
    lg.Layout.Tile='south';
    title(tiles,g.title,'FontSize',22,'Color',[.1 .1 .1]);
    tag=sprintf('BookSim: three-seed means, %d warm-up + %d measured cycles',warmup,measured);
    if isfield(V,'caption'), tag=char(V.caption); end
    if ~V.complete, tag=['Completed-mesh preview. ' tag]; end
    uncertainty='Uncertainty is in individual figures.';
    if ~exportIndividuals, uncertainty='Uncertainty is recorded in summary.csv.'; end
    scaleNote='Each panel starts at zero; y-scales vary to show the measured range.';
    if isfield(V,'warmup_cycles')
        scaleNote='Linear y starts at zero; x/y ranges vary by panel. Drift flags: diagnostics.csv.';
        if strcmp(g.metric,'latency_p99_cycles'), scaleNote='Logarithmic y-axis; x/y ranges vary by panel. Drift flags: diagnostics.csv.'; end
    end
    subtitle(tiles,{tag,scaleNote, ...
        ['Latency covers completed packets. Read it with throughput. ' uncertainty]}, ...
        'FontSize',11,'Color',[.3 .3 .3]);
    saveExports(f,grouped,g.stem); close(f);
    fprintf('Exported comparison page %d/%d\n',i,numel(G));
end
end

function f=baseFigure(cm)
f=figure('Visible','off','Color','w','Units','centimeters','Position',[1 1 cm]);
if isprop(f,'Theme'), f.Theme='light'; end
end

function drawPanel(ax,p,bands)
colors=[0 .447 .698; .835 .369 0; 0 .620 .451]; styles={'-','--','-.'};
hold(ax,'on');
logY=isfield(p,'yscale') && strcmp(p.yscale,'log');
floorY=0; if logY, floorY=1; set(ax,'YScale','log'); end
for ai=1:3
    a=p.series(ai); x=a.x(:); mu=a.mean(:); ci=a.ci95(:);
    if bands
        fill(ax,[x;flipud(x)],[max(floorY,mu-ci);flipud(mu+ci)],colors(ai,:), ...
            'FaceAlpha',.1,'EdgeColor','none','HandleVisibility','off');
    end
    plot(ax,x,mu,'Color',colors(ai,:),'LineStyle',styles{ai},'LineWidth',2.2, ...
        'Marker','none','DisplayName',a.label);
end
set(ax,'FontName','Arial','FontSize',12,'Color','w','XColor',[.15 .15 .15], ...
    'YColor',[.15 .15 .15],'Box','off','TickDir','out','YGrid','on', ...
    'XGrid','off','GridAlpha',.13,'GridColor',[.3 .3 .3]);
if isfield(p,'xlim')
    xlim(ax,p.xlim);
    measuredLoads=p.series(1).x(:);
    tickValues=measuredLoads(round(linspace(1,numel(measuredLoads),5)));
    xticks(ax,tickValues); xticklabels(ax,compose('%.3g',tickValues));
else
    xlim(ax,[10 100]); xticks(ax,[10 30 50 70 100]);
end
if ~logY, ylim(ax,[0 Inf]); end
end

function saveExports(f,folder,stem)
exportgraphics(f,fullfile(folder,[stem '.pdf']),'ContentType','vector');
exportgraphics(f,fullfile(folder,[stem '.png']),'Resolution',300);
savefig(f,fullfile(folder,[stem '.fig']));
end
