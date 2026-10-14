function plot_noc_results(resultDir)
% PLOT_NOC_RESULTS Shared BookSim / NS-2 CSV -> publication figures + MAT file.
% Run: addpath('matlab'); plot_noc_results('results/baseline')
% MATLAB R2020a+; no Statistics toolbox needed for the t intervals.
if nargin < 1, resultDir = fullfile('results','baseline'); end
T = readtable(fullfile(resultDir,'metrics.csv'),'TextType','string');
assert(all(ismember(["simulator","algorithm","status"],string(T.Properties.VariableNames))));
T = T(T.status=="ok",:);
assert(~isempty(T),'No successful simulation rows.');
outputDir = fullfile(resultDir,'matlab_figures');
if ~isfolder(outputDir), mkdir(outputDir); end
save(fullfile(outputDir,'simulation_data.mat'),'T');
metrics = ["latency_p50_cycles","latency_p90_cycles","latency_p99_cycles", ...
    "throughput_flits_per_node_cycle", ...
    "congested_port_time_pct","link_utilization_pct","throughput_offered_pct","wall_seconds"];
labels = ["p50 packet latency (cycles)","p90 packet latency (cycles)","p99 packet latency (cycles)", ...
    "Delivered throughput (flits/node/cycle)", ...
    "Congested port-time (%)","Mean link utilization (%)", ...
    "Delivered / offered traffic (%)","Simulator wall time (s)"];
algorithms = ["xy","dyad","topsis"];
colors = [0 .447 .698; .835 .369 0; 0 .620 .451];
styles = {'-','--','-.'};
for simulator = reshape(unique(T.simulator),1,[])
    for mesh = reshape(unique(T.mesh_k),1,[])
        for traffic = reshape(unique(T.traffic),1,[])
            S = T(T.simulator==simulator & T.mesh_k==mesh & T.traffic==traffic,:);
            if isempty(S), continue; end
            f = figure('Color','w','Units','centimeters','Position',[2 2 39 19],'Visible','off');
            if isprop(f,'Theme'), f.Theme='light'; end
            tiles = tiledlayout(f,2,4,'TileSpacing','compact','Padding','compact');
            for mi = 1:numel(metrics)
                ax = nexttile(tiles); hold(ax,'on');
                for ai = 1:numel(algorithms)
                    A = S(S.algorithm==algorithms(ai),:);
                    loads = unique(A.offered_flits_per_node_cycle);
                    mu = nan(size(loads)); ci = nan(size(loads));
                    for li = 1:numel(loads)
                        values = A.(metrics(mi))(A.offered_flits_per_node_cycle==loads(li));
                        values = values(isfinite(values)); n = numel(values);
                        if n==0, continue; end
                        mu(li)=mean(values);
                        if n>1
                            % Two-sided Student-t 95% quantile via inverse incomplete beta.
                            df=n-1; z=betaincinv(.05,df/2,.5);
                            critical=sqrt(df*(1-z)/z);
                            ci(li)=critical*std(values)/sqrt(n);
                        else
                            ci(li)=0; % Single run has no estimated interval.
                        end
                    end
                    fill(ax,[loads;flipud(loads)],[mu-ci;flipud(mu+ci)],colors(ai,:), ...
                        'FaceAlpha',.12,'EdgeColor','none','HandleVisibility','off');
                    plot(ax,loads,mu,'Color',colors(ai,:),'LineStyle',styles{ai}, ...
                        'LineWidth',1.8,'DisplayName',upper(algorithms(ai)));
                end
                xlabel(ax,'Offered load (flits/node/cycle)'); ylabel(ax,labels(mi));
                set(ax,'FontName','Arial','FontSize',9,'LineWidth',.7,'Box','off', ...
                    'TickDir','out','GridAlpha',.15); grid(ax,'on');
                set(ax,'Color','w','XColor',[.15 .15 .15],'YColor',[.15 .15 .15],'GridColor',[.3 .3 .3]);
                if mi<=3, set(ax,'YScale','log'); end
                if mi>3, ylim(ax,[0 Inf]); end
                if mi==1, legend(ax,'Location','best','Box','off','TextColor',[.1 .1 .1],'Color','w'); end
            end
            if simulator=="booksim", model="flit-level NoC model";
            else, model="packet-level store-and-forward approximation"; end
            title(tiles,sprintf('%s | %d x %d mesh | %s',upper(simulator),mesh,mesh,traffic),'FontSize',15,'Color',[.1 .1 .1]);
            subtitle(tiles,model+"; mean and 95% t-interval across seeds",'FontSize',10,'Color',[.25 .25 .25]);
            stem=sprintf('%s_k%d_%s',simulator,mesh,traffic);
            exportgraphics(f,fullfile(outputDir,stem+".pdf"),'ContentType','vector');
            exportgraphics(f,fullfile(outputDir,stem+".png"),'Resolution',600);
            savefig(f,fullfile(outputDir,stem+".fig"));
            close(f);
        end
    end
end
fprintf('MATLAB outputs: %s\n',outputDir);
end
