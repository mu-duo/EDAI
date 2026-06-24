@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation
REM Build both English and Chinese HTML versions.

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

set SOURCEDIR=source
set BUILDDIR=build
set SPHINXOPTS=-c %SOURCEDIR%

if "%1" == "" goto html_both
if "%1" == "html" goto html_both
if "%1" == "en" goto html_en
if "%1" == "zh" goto html_zh

REM Other targets via Sphinx
%SPHINXBUILD% -M %1 %SOURCEDIR%\en %BUILDDIR%\en %SPHINXOPTS% %O%
%SPHINXBUILD% -M %1 %SOURCEDIR%\zh %BUILDDIR%\zh %SPHINXOPTS% %O%
goto end

:html_en
set EDAI_LANG=en
%SPHINXBUILD% -b html %SOURCEDIR%\en %BUILDDIR%\en %SPHINXOPTS% %O%
echo.
echo.Enlighs build finished. HTML pages are in %BUILDDIR%\en.
goto end

:html_zh
set EDAI_LANG=zh
%SPHINXBUILD% -b html %SOURCEDIR%\zh %BUILDDIR%\zh %SPHINXOPTS% %O%
echo.
echo.Chinese build finished. HTML pages are in %BUILDDIR%\zh.
goto end

:html_both
set EDAI_LANG=en
%SPHINXBUILD% -b html %SOURCEDIR%\en %BUILDDIR%\en %SPHINXOPTS% %O%
echo.Enlighs build finished.

set EDAI_LANG=zh
%SPHINXBUILD% -b html %SOURCEDIR%\zh %BUILDDIR%\zh %SPHINXOPTS% %O%
echo.Chinese build finished.

echo.
echo.Both builds finished. HTML pages are in %BUILDDIR%\en and %BUILDDIR%\zh.
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
echo.
echo.Targets: html (both en+zh), en (English only), zh (Chinese only)
goto end

:end
popd
