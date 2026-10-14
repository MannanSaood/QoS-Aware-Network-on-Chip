function verify_primary_results(resultDir)
% Check the saved, editable figures against the validated measured chart data.
if nargin<1, resultDir=fullfile('results','primary_report'); end
P=jsondecode(fileread(fullfile(resultDir,'figure_data.json')));
G=jsondecode(fileread(fullfile(resultDir,'slide_data.json')));
V=jsondecode(fileread(fullfile(resultDir,'validation.json')));
receipt=struct('complete_study',false,'measured_runs',V.runs, ...
    'checks_passed',false,'status','checking');
writeReceipt(resultDir,receipt);
try
for i=1:numel(P)
    p=P(i); stem=sprintf('k%d_%s_%s',p.mesh_k,p.traffic,p.metric);
    base=fullfile(resultDir,'matlab_figures',stem); checkFiles(base);
    f=openfig([base '.fig'],'invisible'); cleanup=onCleanup(@()close(f));
    ax=findobj(f,'Type','axes'); assert(numel(ax)==1,'Unexpected axes count: %s',stem);
    assert(strcmp(ax.Title.String,sprintf('%dx%d mesh: %s',p.mesh_k,p.mesh_k,p.title)), ...
        'Incorrect mesh or traffic title: %s',stem);
    assert(strcmp(ax.YLabel.String,p.ylabel),'Incorrect metric label: %s',stem);
    checkPanel(ax,p); clear cleanup
end
for i=1:numel(G)
    g=G(i); base=fullfile(resultDir,'comparison_pages',g.stem); checkFiles(base);
    f=openfig([base '.fig'],'invisible'); cleanup=onCleanup(@()close(f));
    axesList=findobj(f,'Type','axes'); assert(numel(axesList)==6,'Expected six traffic panels');
    for j=1:6
        p=g.panels(j);
        selected=axesList(arrayfun(@(a)strcmp(a.Title.String,p.title),axesList));
        assert(numel(selected)==1,'Missing or duplicate traffic title: %s',p.title);
        checkPanel(selected,p);
    end
    clear cleanup
end
receipt=struct('complete_study',V.complete,'measured_runs',V.runs, ...
    'individual_figures',numel(P),'comparison_pages',numel(G), ...
    'verified_lines',3*numel(P)+18*numel(G),'checks_passed',true,'status','passed');
writeReceipt(resultDir,receipt);
fprintf('PASS: %d saved figures; %d plotted lines match measured data, labels and marker requirements\n', ...
    numel(P)+numel(G),receipt.verified_lines);
catch err
    receipt.complete_study=false; receipt.checks_passed=false;
    receipt.status='failed'; receipt.error=err.message;
    writeReceipt(resultDir,receipt);
    rethrow(err);
end
end

function writeReceipt(resultDir,receipt)
file=fopen(fullfile(resultDir,'figure_verification.json'),'w');
assert(file>=0,'Cannot write figure-verification receipt');
cleanup=onCleanup(@()fclose(file)); fprintf(file,'%s\n',jsonencode(receipt,PrettyPrint=true));
end

function checkFiles(base)
for extension={'.fig','.pdf','.png'}
    path=[base extension{1}]; assert(isfile(path),'Missing figure export: %s',path);
    info=dir(path); assert(info.bytes>1000,'Incomplete figure export: %s',path);
end
end

function checkPanel(ax,p)
limits=[10 100]; if isfield(p,'xlim'), limits=p.xlim(:)'; end
assert(isequal(ax.XLim,limits),'Unexpected load range');
if isfield(p,'yscale') && strcmp(p.yscale,'log')
    assert(strcmp(ax.YScale,'log') && ax.YLim(1)>0,'Expected positive logarithmic latency axis');
else
    assert(strcmp(ax.YScale,'linear') && ax.YLim(1)==0,'Expected linear y-axis with zero origin');
end
for j=1:3
    expected=p.series(j);
    plotted=findobj(ax,'Type','line','DisplayName',expected.label);
    assert(numel(plotted)==1,'Missing or duplicate policy curve in %dx%d %s %s: %s', ...
        p.mesh_k,p.mesh_k,p.traffic,p.metric,expected.label);
    assert(strcmp(plotted.Marker,'none'),'Unexpected point markers');
    assert(isequal(plotted.XData(:),expected.x(:)),'Incorrect offered loads');
    assert(numel(plotted.YData)==numel(expected.mean) && ...
        all(abs(plotted.YData(:)-expected.mean(:))<1e-10),'Curve does not match measured values');
end
end
