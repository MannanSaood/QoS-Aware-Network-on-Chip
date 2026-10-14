function plot_model_comparison(resultDir)
% One metric from actual BookSim/NS-2 runs; no universal accuracy ranking.
if nargin<1, resultDir=fullfile('results','model_comparison'); end
P=jsondecode(fileread(fullfile(resultDir,'figure_data.json')));
T=readtable(fullfile(resultDir,'measured_runs.csv'),'TextType','string');
out=fullfile(resultDir,'matlab_figures'); if ~isfolder(out), mkdir(out); end
save(fullfile(resultDir,'simulation_data.mat'),'P','T');
f=figure('Visible','off','Color','w','Units','centimeters','Position',[1 1 23 16]);
if isprop(f,'Theme'), f.Theme='light'; end
ax=axes(f,'Position',[.14 .27 .82 .53]); hold(ax,'on');
colors=[0 .447 .698; .835 .369 0]; styles={'-','--'}; x=(1:4)';
for i=1:2
    mu=P.series(i).mean(:); ci=P.series(i).ci95(:);
    fill(ax,[x;flipud(x)],[max(0,mu-ci);flipud(mu+ci)],colors(i,:), ...
        'FaceAlpha',.10,'EdgeColor','none','HandleVisibility','off');
    plot(ax,x,mu,'LineWidth',2.4,'Marker','none','Color',colors(i,:), ...
        'LineStyle',styles{i},'DisplayName',P.series(i).label);
end
yline(ax,1,':','One-flit/cycle ejection limit','LineWidth',1.2, ...
    'Color',[.3 .3 .3],'HandleVisibility','off','LabelHorizontalAlignment','left');
set(ax,'XTick',1:4,'XTickLabel',{'4x4','8x8','16x16','32x32'}, ...
    'FontName','Arial','FontSize',12,'Box','off','TickDir','out','YGrid','on','GridAlpha',.13);
xlim(ax,[1 4]); ylim(ax,[0 Inf]);
xlabel(ax,'Mesh size'); ylabel(ax,'Aggregate throughput (flits/cycle)');
title(ax,{'Shared destination capacity','XY routing; all-to-one traffic'},'FontSize',15);
legend(ax,'Location','best','Box','off');
annotation(f,'textbox',[.14 .025 .82 .12],'String', ...
    {'Three-seed means and 95% t-intervals; offered injection 0.3 flits/node/cycle.', ...
     '500 warm-up + 1,000 observation cycles. NS-2 omits a shared ejection server.', ...
     'This diagnoses a modeling omission; it is not an accuracy percentage.'}, ...
    'EdgeColor','none','FontName','Arial','FontSize',9,'Color',[.3 .3 .3]);
stem=fullfile(out,'shared_ejection_capacity');
exportgraphics(f,[stem '.pdf'],'ContentType','vector');
exportgraphics(f,[stem '.png'],'Resolution',300); savefig(f,[stem '.fig']); close(f);
fprintf('Exported the measured simulator-model comparison\n');
end
