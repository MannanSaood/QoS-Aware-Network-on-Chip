function plot_project_report(reportDir)
% Traffic-organized single-metric line figures, from verified seed summaries.
if nargin<1, reportDir=fullfile('results','report'); end
specs=jsondecode(fileread(fullfile(reportDir,'figures.json')));
outputDir=fullfile(reportDir,'matlab_figures');
if ~isfolder(outputDir), mkdir(outputDir); end
save(fullfile(outputDir,'report_data.mat'),'specs');
resultsDir=fileparts(reportDir);
scaling=readtable(fullfile(resultsDir,'scaling','metrics.csv'),'TextType','string');
transpose=readtable(fullfile(resultsDir,'transpose_load','metrics.csv'),'TextType','string');
workloads=readtable(fullfile(resultsDir,'workloads','metrics.csv'),'TextType','string');
trafficScaling=readtable(fullfile(resultsDir,'traffic_scaling','metrics.csv'),'TextType','string');
save(fullfile(outputDir,'simulation_data.mat'),'scaling','transpose','workloads','trafficScaling');
colors=[0 .447 .698; .835 .369 0; 0 .620 .451];
styles={'-','--','-.'};
for fi=1:numel(specs)
    s=specs(fi);
    f=figure('Visible','off','Color','w','Units','centimeters','Position',[1 1 23 16]);
    if isprop(f,'Theme'), f.Theme='light'; end
    ax=axes(f,'Position',[.14 .26 .82 .54]); hold(ax,'on');
    for ai=1:numel(s.series)
        a=s.series(ai); x=a.x(:); mu=a.mean(:); ci=a.ci95(:);
        fill(ax,[x;flipud(x)],[max(0,mu-ci);flipud(mu+ci)],colors(ai,:), ...
            'FaceAlpha',.09,'EdgeColor','none','HandleVisibility','off');
        plot(ax,x,mu,'LineStyle',styles{ai},'Color',colors(ai,:), ...
            'LineWidth',2.5,'Marker','none','DisplayName',a.label);
    end
    if ~isempty(s.reference)
        yline(ax,s.reference,':','One-flit/cycle ejection limit','Color',[.3 .3 .3], ...
            'LineWidth',1.3,'HandleVisibility','off','LabelHorizontalAlignment','left');
    end
    set(ax,'FontName','Arial','FontSize',12,'Box','off','TickDir','out', ...
        'Color','w','XColor',[.15 .15 .15],'YColor',[.15 .15 .15], ...
        'GridColor',[.3 .3 .3],'GridAlpha',.12);
    if s.xmesh
        set(ax,'XScale','log','XTick',[4 8 16 32], ...
            'XTickLabel',{'4×4 (16)','8×8 (64)','16×16 (256)','32×32 (1024)'});
    else
        xticks(ax,s.series(1).x);
    end
    xlim(ax,[min(s.series(1).x) max(s.series(1).x)]);
    ylim(ax,[0 Inf]); grid(ax,'on');
    xlabel(ax,s.xlabel); ylabel(ax,s.ylabel);
    title(ax,s.title,'FontSize',16,'FontWeight','bold','Color',[.1 .1 .1]);
    subtitle(ax,s.context,'FontSize',11,'Color',[.3 .3 .3]);
    legend(ax,'Location','best','Box','off','TextColor',[.1 .1 .1],'Color','w');
    annotation(f,'textbox',[.14 .025 .82 .10],'String', ...
        {'Lines: three-seed means; shading: 95% t-intervals.',s.caption}, ...
        'EdgeColor','none','FontName','Arial','FontSize',9,'Color',[.3 .3 .3], ...
        'Interpreter','none');
    stem=string(s.stem);
    exportgraphics(f,fullfile(outputDir,stem+".pdf"),'ContentType','vector');
    exportgraphics(f,fullfile(outputDir,stem+".png"),'Resolution',300);
    savefig(f,fullfile(outputDir,stem+".fig")); close(f);
end
fprintf('Exported %d single-metric MATLAB figures to %s\n',numel(specs),outputDir);
end
